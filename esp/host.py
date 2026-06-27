#!/usr/bin/env python3
import argparse
import struct
import time

import cv2
import serial

REQ_MAGIC = b"\xA5\x5A"
RSP_MAGIC = b"\x5A\xA5"

# Размер кадра, отправляемого на устройство. Препроцессор ESP-DL ImageNetCls сам делает
# resize/crop до входа модели 224x224; 256x256 оставляет небольшой запас под кроп.
SEND_SIZE = 256
JPEG_QUALITY = 80


def read_until_magic(ser, magic, timeout_s=3.0):
    """Побайтно сканирует поток serial, пока не встретит `magic`. Возвращает True при успехе.

    Логи загрузки / вывод ESP_LOG делят тот же канал USB-Serial-JTAG, поэтому мы никогда не
    считаем, что следующие байты — наши: ресинхронизируемся по магическому префиксу каждый раз.
    """
    deadline = time.time() + timeout_s
    window = b""
    while time.time() < deadline:
        b = ser.read(1)
        if not b:
            continue
        window = (window + b)[-2:]
        if window == magic:
            return True
    return False


def read_response(ser, timeout_s=3.0):
    """Читает одну строку ответа до '\\n' после магического заголовка. Возвращает str или None."""
    if not read_until_magic(ser, RSP_MAGIC, timeout_s):
        return None
    line = bytearray()
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        b = ser.read(1)
        if not b:
            continue
        if b == b"\n":
            break
        line += b
    try:
        return line.decode("utf-8", errors="replace").strip()
    except Exception:
        return None


def send_frame(ser, jpeg_bytes):
    header = REQ_MAGIC + struct.pack("<I", len(jpeg_bytes))
    ser.write(header)
    ser.write(jpeg_bytes)
    ser.flush()


def main():
    ap = argparse.ArgumentParser(description="Хост инференса MobileNetV2 на ESP32-S3 по USB")
    ap.add_argument("--port", default="/dev/cu.usbmodem101",
                    help="serial-порт нативного USB ESP32-S3 (по умолчанию: /dev/cu.usbmodem101)")
    ap.add_argument("--baud", type=int, default=921600,
                    help="скорость (игнорируется USB-CDC, но требуется pyserial)")
    ap.add_argument("--camera", type=int, default=0, help="индекс камеры OpenCV")
    ap.add_argument("--debug", action="store_true",
                    help="печатать сырые ответы ESP и предупреждать о таймаутах")
    args = ap.parse_args()

    print(f"[host] открываю serial {args.port} ...")
    ser = serial.Serial(args.port, args.baud, timeout=0.1)
    time.sleep(0.5)
    ser.reset_input_buffer()

    print(f"[host] открываю камеру {args.camera} ...")
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit(f"не удалось открыть камеру {args.camera}")

    enc_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
    last_label, last_score, last_dev_ms = "...", 0.0, 0.0
    fps = 0.0
    misses = 0  # подряд идущие кадры без ответа

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            square = cv2.resize(frame, (SEND_SIZE, SEND_SIZE))
            ok, buf = cv2.imencode(".jpg", square, enc_params)
            if not ok:
                continue

            t0 = time.time()
            send_frame(ser, buf.tobytes())
            resp = read_response(ser)
            rtt_ms = (time.time() - t0) * 1000.0

            if resp:
                misses = 0
                if args.debug:
                    print(f"[host] ответ: {resp!r}  rtt={rtt_ms:.0f} мс")
                parts = resp.split("|")
                if len(parts) == 3:
                    last_label = parts[0]
                    try:
                        last_score = float(parts[1])
                        last_dev_ms = float(parts[2])
                    except ValueError:
                        pass
                # Немного сглаживаем round-trip FPS.
                inst_fps = 1000.0 / rtt_ms if rtt_ms > 0 else 0.0
                fps = 0.8 * fps + 0.2 * inst_fps if fps else inst_fps
            else:
                # Нет ответа -> оверлей остался бы на нулях. Делаем это видимым, а не молчим.
                misses += 1
                fps = 0.0
                if args.debug or misses <= 3 or misses % 20 == 0:
                    print(f"[host] нет ответа от ESP (таймаут {rtt_ms:.0f} мс), пропусков подряд: {misses}. "
                          f"Проверьте: верный --port, прошивка свежая (idf.py flash), "
                          f"консоль НЕ на USB-Serial-JTAG, monitor не запущен.")

            # Накладываем на полноразмерный кадр. Текст оверлея — латиницей: встроенные
            # шрифты Hershey в OpenCV не умеют рисовать кириллицу (она вышла бы как "?????").
            cv2.putText(frame, f"{last_label}  {last_score:.2f}",
                        (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.putText(frame, f"device {last_dev_ms:.0f} ms | round-trip {fps:.1f} FPS",
                        (12, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow("Edge AI - ESP32-S3 MobileNetV2 (USB)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        ser.close()
        print("[host] закрыто.")


if __name__ == "__main__":
    main()
