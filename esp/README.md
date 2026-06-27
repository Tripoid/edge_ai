# ESP32-S3

Ноутбук отправляет кадры по нативному USB (USB-Serial-JTAG) на **ESP32-S3-DevKitC-1 N16R8**,
плата прогоняет **MobileNetV2 INT8** через ESP-DL и возвращает топ-1 класс и латентность (Отдельного модуля камеры у меня не было, только сама esp).

## Состав

| Файл | Назначение |
|------|-----------|
| `mobilenetv2_usb/` | ESP-IDF прошивка, на базе `esp-dl/examples/mobilenetv2_cls` |
| `host.py` | Самописный режим монитора вместо встроеннного |
| `quantize_mnv2.py` | MobileNetV2 в INT8 `.espdl` через esp-ppq|

## Запуск

```bash
cd mobilenetv2_usb
idf.py set-target esp32s3 && idf.py build
idf.py -p <порт> flash
cd .. && pip install -r requirements.txt
python host.py --port <порт> --debug
```

## Результат

MobileNetV2 224×224 INT8 на ESP32-S3: инференс ≈ **2754 мс/кадр**, **0,4 FPS**.

## Источники

- ESP-DL (пример MobileNetV2) - https://github.com/espressif/esp-dl/tree/master/examples/mobilenetv2_cls
- ESP-IDF (USB-Serial-JTAG echo) - https://github.com/espressif/esp-idf/tree/master/examples/peripherals/usb_serial_jtag/usb_serial_jtag_echo
- esp-ppq (квантизация) - https://github.com/espressif/esp-ppq
