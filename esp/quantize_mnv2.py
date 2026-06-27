#!/usr/bin/env python3
import argparse

import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import MobileNet_V2_Weights, mobilenet_v2

from esp_ppq.api import espdl_quantize_torch

DEVICE = "cpu"
TARGET = "esp32s3"          # аппаратная цель для esp-ppq
NUM_OF_BITS = 8            # INT8 PTQ
INPUT_SHAPE = [1, 3, 224, 224]

# Стандартный препроцессинг ImageNet (совпадает с torchvision MobileNet_V2_Weights.IMAGENET1K_V1).
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_calib_loader(calib_dir, batch_size=32):

    tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    dataset = ImageFolder(calib_dir, transform=tf)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)


def main():
    ap = argparse.ArgumentParser(description="Квантизация MobileNetV2 в INT8 .espdl (ESP32-S3)")
    ap.add_argument("--calib-dir", required=True,
                    help="папка с реальными изображениями ImageNet в раскладке ImageFolder (подпапки-классы)")
    ap.add_argument("--out", default="mobilenetv2_224_int8.espdl",
                    help="путь выходного .espdl")
    ap.add_argument("--calib-steps", type=int, default=32, help="число шагов калибровки")
    args = ap.parse_args()

    # Предобученная float MobileNetV2 из torchvision.
    model = mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1).to(DEVICE).eval()

    calib_loader = build_calib_loader(args.calib_dir)

    # esp-ppq прогоняет каждый батч через collate_fn; нам нужен только тензор изображения на DEVICE.
    def collate_fn(batch):
        images, _labels = batch
        return images.to(DEVICE)

    espdl_quantize_torch(
        model=model,
        espdl_export_file=args.out,
        calib_dataloader=calib_loader,
        calib_steps=args.calib_steps,
        input_shape=INPUT_SHAPE,
        inputs=None,
        target=TARGET,
        num_of_bits=NUM_OF_BITS,
        collate_fn=collate_fn,
        dispatching_override=None,
        device=DEVICE,
        error_report=True,
        skip_export=False,
        export_test_values=False,
        verbose=1,
    )
    print(f"[quantize] записан {args.out}")


if __name__ == "__main__":
    main()
