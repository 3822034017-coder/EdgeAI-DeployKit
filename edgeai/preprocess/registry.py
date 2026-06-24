from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from ..model_signature import analyze_package
from ..package_layout import load_json, package_paths, save_json
from .image import prepare_image_input
from .tensor import prepare_tensor_input

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _first_input(signature: Dict[str, Any]) -> Dict[str, Any]:
    inputs = signature.get("inputs") or []
    if not inputs:
        raise ValueError("model has no runtime inputs")
    if len(inputs) > 1:
        # 第一版先支持单输入，多输入后续扩展。
        raise ValueError(f"multiple inputs are not supported in this foundation patch: {[x.get('name') for x in inputs]}")
    return inputs[0]


def infer_default_preprocess(signature: Dict[str, Any]) -> Dict[str, Any]:
    inp = _first_input(signature)
    shape: List[Any] = inp.get("shape") or []
    layout = inp.get("layout_guess") or "unknown"
    dtype = inp.get("dtype") or "float32"

    if len(shape) == 4 and layout in ("NCHW", "NHWC"):
        if layout == "NCHW":
            c = shape[1] if isinstance(shape[1], int) else 3
            h = shape[2] if isinstance(shape[2], int) else 224
            w = shape[3] if isinstance(shape[3], int) else 224
        else:
            h = shape[1] if isinstance(shape[1], int) else 224
            w = shape[2] if isinstance(shape[2], int) else 224
            c = shape[3] if isinstance(shape[3], int) else 3
        return {
            "input_type": "image",
            "input_name": inp.get("name"),
            "layout": layout,
            "color_format": "GRAY" if c == 1 else "RGB",
            "resize": {"mode": "resize", "width": int(w), "height": int(h)},
            "normalization": {"scale": 1.0 / 255.0, "mean": [0, 0, 0] if c != 1 else [0], "std": [1, 1, 1] if c != 1 else [1]},
            "dtype": "float32" if "float" in dtype else dtype,
            "note": "auto-generated from ONNX input shape; please confirm it matches the training preprocessing.",
        }

    return {
        "input_type": "tensor",
        "input_name": inp.get("name"),
        "shape": shape,
        "dtype": "float32" if "float" in dtype else dtype,
        "note": "auto-generated generic tensor preprocessing; provide .npy input or edit preprocess.json.",
    }


def prepare_package_input(package_dir: Path, input_path: Path, preprocess_path: Path | None = None, force_analyze: bool = False) -> Dict[str, Any]:
    paths = package_paths(Path(package_dir))
    if force_analyze or not paths.model_signature_json.exists():
        analyze_package(paths.root)
    signature = load_json(paths.model_signature_json)
    inp = _first_input(signature)
    input_shape = inp.get("shape") or []

    if preprocess_path:
        preprocess = load_json(Path(preprocess_path))
    elif paths.preprocess_json.exists():
        preprocess = load_json(paths.preprocess_json)
    else:
        preprocess = infer_default_preprocess(signature)
        save_json(paths.preprocess_json, preprocess)

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")

    # 保存一份原始输入，便于报告追溯。
    source_copy = paths.root / f"source_input{input_path.suffix.lower()}"
    if source_copy.exists():
        source_copy.unlink()
    shutil.copy2(input_path, source_copy)

    input_type = (preprocess.get("input_type") or "").lower()
    suffix = input_path.suffix.lower()
    if input_type == "image" or suffix in _IMAGE_EXTS:
        result = prepare_image_input(input_path, paths.input_npy, preprocess, input_shape)
    elif input_type == "tensor" or suffix == ".npy":
        result = prepare_tensor_input(input_path, paths.input_npy, preprocess, input_shape)
    else:
        raise ValueError(f"unsupported input_type={input_type!r}, suffix={suffix!r}; first patch supports image and .npy tensor")

    result["preprocess_json"] = str(paths.preprocess_json)
    result["source_input"] = str(source_copy)
    result["model_input"] = inp
    return result
