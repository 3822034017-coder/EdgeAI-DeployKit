#!/usr/bin/env python3
"""Create input.npy from B-side JSON and an optional image.

This runs on the development machine. The board-side run_model.py then consumes
input.npy directly and does not need cv2/Pillow.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np

from .json_contract import normalize_json_file


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def dtype_to_numpy(dtype: str):
    mapping = {
        "float32": np.float32,
        "float64": np.float64,
        "int64": np.int64,
        "int32": np.int32,
        "uint8": np.uint8,
    }
    return mapping.get(dtype.lower(), np.float32)


def make_dummy(shape: list[int], dtype: str, mode: str):
    np_dtype = dtype_to_numpy(dtype)
    size = int(np.prod(shape))
    if mode == "ones":
        arr = np.ones(size, dtype=np_dtype)
    elif mode == "range":
        arr = (np.arange(size) % 255).astype(np.float32) / 255.0
        arr = arr.astype(np_dtype)
    else:
        arr = np.zeros(size, dtype=np_dtype)
    return arr.reshape(shape)


def preprocess_image(image_path: Path, contract: dict):
    from PIL import Image

    shape = contract["input_shape"]
    dtype = dtype_to_numpy(contract["input_dtype"])
    layout = contract["input_format"].upper()
    model_type = contract["model_type"]

    if len(shape) != 4:
        raise ValueError(f"image preprocessing expects 4D input, got {shape}")

    if layout == "NCHW":
        _, channels, height, width = shape
    elif layout == "NHWC":
        _, height, width, channels = shape
    else:
        _, channels, height, width = shape

    if channels == 1:
        image = Image.open(image_path).convert("L").resize((width, height))
        arr = np.asarray(image).astype(np.float32)
        if model_type == "mnist":
            arr = arr / 255.0
            arr = arr / 0.3081
            arr = arr - 0.1307 / 0.3081
        else:
            arr = arr / 255.0
        if layout == "NHWC":
            arr = arr.reshape(1, height, width, 1)
        else:
            arr = arr.reshape(1, 1, height, width)
    else:
        image = Image.open(image_path).convert("RGB").resize((width, height))
        arr = np.asarray(image).astype(np.float32) / 255.0
        if model_type in {"mobilenetv2", "resnet18"}:
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            arr = (arr - mean) / std
        if layout == "NCHW":
            arr = arr.transpose(2, 0, 1).reshape(1, channels, height, width)
        else:
            arr = arr.reshape(1, height, width, channels)

    return arr.astype(dtype)


def load_tensor_file(input_path: Path, contract: dict):
    shape = contract["input_shape"]
    dtype = dtype_to_numpy(contract["input_dtype"])
    suffix = input_path.suffix.lower()

    if suffix == ".npy":
        arr = np.load(input_path)
    elif suffix in {".bin", ".raw"}:
        arr = np.fromfile(input_path, dtype=dtype)
    elif suffix in {".txt", ".csv"}:
        delimiter = "," if suffix == ".csv" else None
        arr = np.loadtxt(input_path, delimiter=delimiter)
    else:
        raise ValueError(
            f"unsupported input file: {input_path}. "
            "Use image, .npy, .bin, .raw, .txt, or .csv."
        )

    arr = arr.astype(dtype, copy=False)
    if list(arr.shape) == shape:
        return arr

    expected = int(np.prod(shape))
    if arr.size != expected:
        raise ValueError(
            f"input file has {arr.size} values, but JSON shape {shape} needs {expected}"
        )
    return arr.reshape(shape)


def prepare_input_file(input_path: Path, contract: dict):
    if input_path.suffix.lower() in IMAGE_SUFFIXES:
        return preprocess_image(input_path, contract)
    return load_tensor_file(input_path, contract)


def create_input_npy(
    json_path: Path,
    output_path: Path,
    image_path: Optional[Path] = None,
    dummy_mode: str = "zeros",
) -> Path:
    contract = normalize_json_file(Path(json_path).expanduser().resolve())
    if image_path:
        tensor = prepare_input_file(Path(image_path).expanduser().resolve(), contract)
    else:
        tensor = make_dummy(contract["input_shape"], contract["input_dtype"], dummy_mode)

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.save(output, tensor)
    print(f"[OK] saved {output}")
    print(f"[INFO] shape={list(tensor.shape)} dtype={tensor.dtype} bytes={tensor.nbytes}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate input.npy according to model JSON.")
    parser.add_argument("--json", required=True, help="B-side model JSON / model_profile.json")
    parser.add_argument("-i", "--input", help="optional input image/tensor file")
    parser.add_argument("--image", help="compatibility alias for --input")
    parser.add_argument("-o", "--output", default="input.npy")
    parser.add_argument("--dummy", choices=("zeros", "ones", "range"), default="zeros")
    args = parser.parse_args()

    input_file = args.input or args.image
    create_input_npy(
        json_path=Path(args.json),
        output_path=Path(args.output),
        image_path=Path(input_file) if input_file else None,
        dummy_mode=args.dummy,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
