# MacBook

Нативное приложение (SwiftUI + AVFoundation + Vision + Core ML), классифицирует поток с
камеры Mac и показывает топ-1 класс и латентность. Модель - MobileNetV3-Small.
Реализовано на примере Apple «Classifying Images with Vision and Core ML».

## Запуск

```bash
open EdgeAIMac/EdgeAIMac.xcodeproj
```
 Запуск


## Результат

MobileNetV3-Small на Apple Neural Engine: инференс **5–9 мс**, ~30 FPS.

## Источники

- Classifying Images with Vision and Core ML - https://developer.apple.com/documentation/vision/classifying-images-with-vision-and-core-ml
- AVCaptureVideoDataOutput - https://developer.apple.com/documentation/avfoundation/avcapturevideodataoutput
- coremltools - https://github.com/apple/coremltools
- torchvision models - https://github.com/pytorch/vision
