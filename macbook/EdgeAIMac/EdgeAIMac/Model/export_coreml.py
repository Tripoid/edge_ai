#!/usr/bin/env python3
import numpy as np
import torch
import torch.nn as nn
import coremltools as ct
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

OUT = "MobileNetV3Small.mlpackage"
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class Normalized(nn.Module):
    """Обёртка модели, чтобы вход-изображение Core ML оставался простым (scale 1/255, bias 0):
    пиксели приходят в [0,1], применяем поканальную нормализацию ImageNet, затем softmax."""

    def __init__(self, base: nn.Module):
        super().__init__()
        self.base = base
        self.register_buffer("mean", torch.tensor(IMAGENET_MEAN).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor(IMAGENET_STD).view(1, 3, 1, 1))

    def forward(self, x):
        x = (x - self.mean) / self.std
        return torch.softmax(self.base(x), dim=1)


def main():
    weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1
    labels = weights.meta["categories"]  # 1000 человекочитаемых меток ImageNet

    model = Normalized(mobilenet_v3_small(weights=weights)).eval()

    example = torch.rand(1, 3, 224, 224)
    traced = torch.jit.trace(model, example)

    # ct.ImageType: удобный для Vision RGB-вход. scale=1/255 переводит пиксели [0,255] -> [0,1].
    image_input = ct.ImageType(
        name="image",
        shape=(1, 3, 224, 224),
        scale=1.0 / 255.0,
        bias=[0.0, 0.0, 0.0],
        color_layout=ct.colorlayout.RGB,
    )

    mlmodel = ct.convert(
        traced,
        inputs=[image_input],
        classifier_config=ct.ClassifierConfig(class_labels=list(labels)),
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.macOS13,
    )
    mlmodel.short_description = "Классификатор ImageNet MobileNetV3-Small (демо Edge AI)"
    mlmodel.save(OUT)
    print(f"[export] записан {OUT}")

    # Небольшая проверка, что файл загружается.
    _ = ct.models.MLModel(OUT)
    print("[export] перезагрузка OK")


if __name__ == "__main__":
    main()
