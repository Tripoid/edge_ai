#include <stdio.h>
#include <string.h>
#include <vector>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "driver/usb_serial_jtag.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_err.h"
#include "esp_heap_caps.h"

#include "dl_image_jpeg.hpp" // dl::image::jpeg_img_t, dl::image::sw_decode_jpeg
#include "imagenet_cls.hpp" // ImageNetCls

static const char *TAG = "mnv2_usb";

// Байты синхронизации (магические заголовки).
static const uint8_t REQ_MAGIC0 = 0xA5;
static const uint8_t REQ_MAGIC1 = 0x5A;
static const uint8_t RSP_MAGIC0 = 0x5A;
static const uint8_t RSP_MAGIC1 = 0xA5;

// Кольцевые буферы USB-Serial-JTAG. Кадр JPEG 256x256 — это ~10-30 КБ, поэтому кадр
// вычитываем из кольца порциями, а не делаем кольцо размером с целый кадр. RX берём с
// запасом, чтобы всплеск входных байт не переполнил кольцо (потеря байт -> read_exact
// зависнет в ожидании недостающего «хвоста» кадра и ответа не будет).
#define USB_RX_BUF_SIZE 16384
#define USB_TX_BUF_SIZE 4096

// Жёсткий потолок на входной JPEG, чтобы битое поле длины не разнесло кучу.
#define MAX_JPEG_BYTES (512 * 1024)

// Прочитать ровно n байт из USB-Serial-JTAG, блокируясь, пока не придёт вся порция.
static void read_exact(uint8_t *buf, size_t n)
{
    size_t got = 0;
    while (got < n) {
        int r = usb_serial_jtag_read_bytes(buf + got, n - got, portMAX_DELAY);
        if (r > 0) {
            got += (size_t)r;
        }
    }
}

// Блокируемся, пока на проводе не встретится двухбайтовый магический заголовок запроса
// (0xA5 0x5A). Посторонний текст загрузки/логов на том же канале USB-Serial-JTAG безвреден:
// он просто никогда не совпадёт с магической последовательностью и будет пропущен.
static void wait_for_request_magic(void)
{
    uint8_t c;
    int state = 0; // 0: ищем MAGIC0, 1: видели MAGIC0, ждём MAGIC1
    while (true) {
        read_exact(&c, 1);
        if (state == 0) {
            if (c == REQ_MAGIC0) state = 1;
        } else {
            if (c == REQ_MAGIC1) return;
            else state = (c == REQ_MAGIC0) ? 1 : 0;
        }
    }
}

static void send_response(const char *line)
{
    uint8_t hdr[2] = {RSP_MAGIC0, RSP_MAGIC1};
    usb_serial_jtag_write_bytes((const char *)hdr, sizeof(hdr), portMAX_DELAY);
    usb_serial_jtag_write_bytes(line, strlen(line), portMAX_DELAY);
    // Установленный драйвер сам опустошает TX-кольцо из своего прерывания; ответы
    // маленькие и отправляются на каждый кадр, поэтому ручной flush FIFO не нужен
    // (а низкоуровневый LL-flush конфликтовал бы с драйвером за периферию).
}

extern "C" void app_main(void)
{
    // Держим канал максимально чистым для бинарного протокола.
    esp_log_level_set("*", ESP_LOG_ERROR);

    usb_serial_jtag_driver_config_t usb_cfg = {
        .tx_buffer_size = USB_TX_BUF_SIZE,
        .rx_buffer_size = USB_RX_BUF_SIZE,
    };
    // Не валим всё приложение в reboot-loop, если установка драйвера не удалась
    // (например, периферию уже забрала консоль — см. sdkconfig.defaults). Логи уходят
    // на UART, так что эту ошибку видно через UART-порт.
    esp_err_t err = usb_serial_jtag_driver_install(&usb_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "usb_serial_jtag_driver_install failed: %s", esp_err_to_name(err));
    }

    // Создаём классификатор один раз; арена esp-dl живёт в PSRAM (нужна OPI PSRAM на N16R8).
    ImageNetCls *cls = new ImageNetCls();

    // Переиспользуемый буфер приёма JPEG в PSRAM, растёт по мере необходимости.
    uint8_t *jpeg_buf = nullptr;
    size_t   jpeg_cap = 0;

    char out_line[160];

    while (true) {
        wait_for_request_magic();

        // Длина: uint32 little-endian.
        uint8_t lenbuf[4];
        read_exact(lenbuf, 4);
        uint32_t jlen = (uint32_t)lenbuf[0] |
                        ((uint32_t)lenbuf[1] << 8) |
                        ((uint32_t)lenbuf[2] << 16) |
                        ((uint32_t)lenbuf[3] << 24);

        if (jlen == 0 || jlen > MAX_JPEG_BYTES) {
            // Полезного нечего вычитывать; просто ресинхронизируемся на следующем кадре.
            send_response("__error_badlen|0.000|0.0\n");
            continue;
        }

        if (jlen > jpeg_cap) {
            if (jpeg_buf) heap_caps_free(jpeg_buf);
            jpeg_buf = (uint8_t *)heap_caps_malloc(jlen, MALLOC_CAP_SPIRAM);
            jpeg_cap = jpeg_buf ? jlen : 0;
            if (!jpeg_buf) {
                send_response("__error_oom|0.000|0.0\n");
                continue;
            }
        }

        read_exact(jpeg_buf, jlen);

        // Декодируем JPEG -> RGB888 (программный декодер esp-dl).
        dl::image::jpeg_img_t jpeg_img = {
            .data = (void *)jpeg_buf,
            .data_len = (size_t)jlen,
        };
        dl::image::img_t img = dl::image::sw_decode_jpeg(jpeg_img, dl::image::DL_IMAGE_PIX_TYPE_RGB888);
        if (!img.data) {
            send_response("__error_decode|0.000|0.0\n");
            continue;
        }

        // Инференс, замер микросекундным высокоточным таймером.
        int64_t t0 = esp_timer_get_time();
        std::vector<dl::cls::result_t> &results = cls->run(img);
        int64_t t1 = esp_timer_get_time();
        float latency_ms = (float)(t1 - t0) / 1000.0f;

        if (!results.empty()) {
            snprintf(out_line, sizeof(out_line), "%s|%.3f|%.1f\n",
                     results[0].cat_name, results[0].score, latency_ms);
        } else {
            snprintf(out_line, sizeof(out_line), "__no_result|0.000|%.1f\n", latency_ms);
        }
        send_response(out_line);

        heap_caps_free(img.data);
    }
}
