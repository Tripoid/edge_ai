# jupyter — исследования и замеры

Ноутбук `edge_ai.ipynb` повторяет выкладки реферата реальными запусками: загрузка
MobileNetV2 и V3-Small, экспорт в ONNX и Core ML, сравнение размеров и латентности на CPU,
INT8-квантизация и причина несовместимости SE-блоков с ESP-DL. Без TensorFlow.

## Запуск

```bash
cd jupyter
python3.11 -m venv .venv && source .venv/bin/activate   # coremltools требует Python < 3.13
pip install -r requirements.txt
jupyter notebook edge_ai.ipynb        # выполнить сверху вниз
```

Все числа вычисляются в ячейках, ничего не зашито. Артефакты пишутся в `artifacts/`.

## Ключевой результат

| Модель | Параметры | CPU, мс | ONNX, МБ | Core ML, МБ | SE-блоки |
|--------|-----------|---------|----------|-------------|----------|
| MobileNetV2 | 3,5 млн | 18,3 | 14,2 | 7,1 | 0 |
| MobileNetV3-Small | 2,5 млн | 29,3 | 10,5 | 5,2 | 9 |

## Источники

- torchvision models — https://github.com/pytorch/vision
- PyTorch ONNX export — https://pytorch.org/docs/stable/onnx.html
- coremltools — https://github.com/apple/coremltools
