from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import numpy as np


def prepare_tensor_input(input_path: Path, output_path: Path, preprocess: Dict[str, Any], input_shape: List[Any]) -> Dict[str, Any]:
    input_path = Path(input_path)
    if input_path.suffix.lower() != ".npy":
        raise ValueError("tensor input currently requires .npy")
    arr = np.load(input_path)
    dtype = preprocess.get("dtype")
    if dtype:
        arr = arr.astype(dtype)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, arr)
    return {
        "ok": True,
        "input_type": "tensor",
        "source": str(input_path),
        "output": str(output_path),
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
    }
