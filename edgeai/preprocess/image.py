from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


def _target_hw_and_channels(shape: List[Any], layout: str) -> Tuple[int, int, int]:
    if len(shape) != 4:
        raise ValueError(f"image model expects rank-4 shape, got {shape}")
    if layout == "NCHW":
        c = int(shape[1]) if isinstance(shape[1], int) else 3
        h = int(shape[2]) if isinstance(shape[2], int) else 224
        w = int(shape[3]) if isinstance(shape[3], int) else 224
    elif layout == "NHWC":
        h = int(shape[1]) if isinstance(shape[1], int) else 224
        w = int(shape[2]) if isinstance(shape[2], int) else 224
        c = int(shape[3]) if isinstance(shape[3], int) else 3
    else:
        raise ValueError(f"unknown image layout: {layout}")
    return h, w, c


def prepare_image_input(input_path: Path, output_path: Path, preprocess: Dict[str, Any], input_shape: List[Any]) -> Dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("需要安装 Pillow: pip install pillow") from exc

    layout = (preprocess.get("layout") or "NCHW").upper()
    h, w, channels = _target_hw_and_channels(input_shape, layout)
    resize_cfg = preprocess.get("resize") or {}
    resize_w = int(resize_cfg.get("width") or w)
    resize_h = int(resize_cfg.get("height") or h)
    color_format = (preprocess.get("color_format") or ("GRAY" if channels == 1 else "RGB")).upper()

    img = Image.open(input_path)
    if channels == 1 or color_format == "GRAY":
        img = img.convert("L")
    else:
        img = img.convert("RGB")
    img = img.resize((resize_w, resize_h))

    arr = np.asarray(img)
    if arr.ndim == 2:
        arr = arr[:, :, None]
    if color_format == "BGR" and arr.shape[-1] == 3:
        arr = arr[:, :, ::-1]

    arr = arr.astype(np.float32)
    norm = preprocess.get("normalization") or {}
    scale = float(norm.get("scale", 1.0 / 255.0))
    arr = arr * scale

    mean = norm.get("mean")
    std = norm.get("std")
    if mean is not None:
        mean_arr = np.asarray(mean, dtype=np.float32).reshape(1, 1, -1)
        arr = arr - mean_arr
    if std is not None:
        std_arr = np.asarray(std, dtype=np.float32).reshape(1, 1, -1)
        arr = arr / np.maximum(std_arr, 1e-12)

    if layout == "NCHW":
        arr = np.transpose(arr, (2, 0, 1))[None, ...]
    else:
        arr = arr[None, ...]

    dtype = preprocess.get("dtype", "float32")
    arr = arr.astype(dtype)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, arr)

    return {
        "ok": True,
        "input_type": "image",
        "source": str(input_path),
        "output": str(output_path),
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "layout": layout,
        "resize": {"width": resize_w, "height": resize_h},
        "color_format": color_format,
    }
