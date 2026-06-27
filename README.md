# Edge AI - практическая часть

Инференс лёгкой свёрточной сети (семейство **MobileNet**) **в реальном времени** с камеры
на трёх классах устройств и jupyter ноутбук. Стек: **PyTorch, Core ML, ONNX,
ESP-DL**.

| Папка | Устройство | Модель | Фреймворк |
|-------|------------|--------|-----------|
| [`jupyter/`](jupyter/) | Ноутбук (CPU) | MobileNetV2 / V3-Small | PyTorch, ONNX, Core ML |
| [`macbook/`](macbook/) | macOS (M4) | MobileNetV3-Small | Swift, Vision, Core ML |
| [`iphone/`](iphone/) | iPhone 15 (A16) | MobileNetV3-Small | Swift, Vision, Core ML |
| [`esp/`](esp/) | ESP32-S3 | **MobileNetV2 (INT8)** | C/C++, ESP-IDF, ESP-DL |

На ESP32 - MobileNetV2, а не V3-Small: squeeze-and-excite блоки V3-Small не квантуются под
ESP-DL (подробнее в [`esp/README.md`](esp/README.md) и в 6 ячейке ноутбука).

## Результаты

| Платформа | Модель | Точность | Латентность | FPS |
|-----------|--------|----------|-------------|-----|
| MacBook Air M4 (ANE) | MobileNetV3-Small | fp16 | 5-9 мс | ~30 |
| iPhone 15 (ANE) | MobileNetV3-Small | fp16 | 11-14 мс | ~30 |
| ESP32-S3 (ESP-DL) | MobileNetV2 | INT8 | ≈2754 мс | ~0,4 |


## Как запускать

В каждой папке свой README с шагами. Кратко:

- **jupyter** - `pip install -r requirements.txt`, открыть `edge_ai.ipynb`, выполнить сверху вниз.
- **macbook** - `open macbook/EdgeAIMac/EdgeAIMac.xcodeproj`, запуск.
- **iphone** - `open iphone/EdgeAIiOS/EdgeAIiOS.xcodeproj`, выбрать целевое устройство, запустить.
- **esp** - `idf.py build && idf.py -p <порт> flash`, затем `python esp/host.py --port <порт>`.

## Источники

- ESP-DL - https://github.com/espressif/esp-dl
- ESP-IDF - https://github.com/espressif/esp-idf
- esp-ppq - https://github.com/espressif/esp-ppq
- Apple «Classifying Images with Vision and Core ML» - https://developer.apple.com/documentation/vision/classifying-images-with-vision-and-core-ml
- coremltools - https://github.com/apple/coremltools
- torchvision models - https://github.com/pytorch/vision
