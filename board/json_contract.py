#!/usr/bin/env python3
"""Flexible JSON contract helpers for B/C/D integration.

B-side tools may produce slightly different JSON layouts. This module normalizes
them into one deployment contract consumed by package, board-sync, ATC convert,
and generic board-side inference.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_DTYPES = {
    "mnist": "float32",
    "mobilenetv2": "float32",
    "resnet18": "float32",
    "yolov5n": "float32",
}

DEFAULT_SHAPES = {
    "mnist": [1, 1, 28, 28],
    "mobilenetv2": [1, 3, 224, 224],
    "resnet18": [1, 3, 224, 224],
    "yolov5n": [1, 3, 640, 640],
}

DEFAULT_LAYOUTS = {
    "mnist": "NCHW",
    "mobilenetv2": "NCHW",
    "resnet18": "NCHW",
    "yolov5n": "NCHW",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _first_present(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


def _first_input(data: dict[str, Any]) -> dict[str, Any]:
    inputs = data.get("inputs") or data.get("model_inputs") or data.get("onnx_inputs") or []
    if isinstance(inputs, list) and inputs:
        first = inputs[0]
        if isinstance(first, dict):
            return first
        if isinstance(first, str):
            input_shapes = data.get("input_shapes") or data.get("shapes") or {}
            return {"name": first, "shape": input_shapes.get(first)}
    if isinstance(inputs, dict) and inputs:
        name, value = next(iter(inputs.items()))
        if isinstance(value, dict):
            merged = dict(value)
            merged.setdefault("name", name)
            return merged
        return {"name": name, "shape": value}
    onnx = data.get("onnx") or {}
    if isinstance(onnx, dict):
        onnx_inputs = onnx.get("inputs") or []
        if isinstance(onnx_inputs, list) and onnx_inputs and isinstance(onnx_inputs[0], dict):
            return onnx_inputs[0]
    return {}


def _first_outputs(data: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = data.get("outputs") or data.get("model_outputs") or data.get("onnx_outputs")
    if outputs is None and isinstance(data.get("onnx"), dict):
        outputs = data["onnx"].get("outputs")
    if isinstance(outputs, list):
        return [item if isinstance(item, dict) else {"name": str(item)} for item in outputs]
    if isinstance(outputs, dict):
        return [{"name": name, **(value if isinstance(value, dict) else {})} for name, value in outputs.items()]
    names = data.get("output_names") or []
    if isinstance(names, list):
        return [{"name": str(name)} for name in names]
    return []


def normalize_shape(shape: Any, fallback: list[int]) -> list[int]:
    if isinstance(shape, str):
        if ":" in shape:
            shape = shape.split(":", 1)[1]
        parts = shape.replace("x", ",").split(",")
        values = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            try:
                values.append(int(part))
            except ValueError:
                values.append(-1)
        shape = values
    if isinstance(shape, tuple):
        shape = list(shape)
    if isinstance(shape, list) and shape:
        result = []
        for idx, value in enumerate(shape):
            if isinstance(value, int) and value > 0:
                result.append(value)
            else:
                result.append(fallback[idx] if idx < len(fallback) else 1)
        return result
    return list(fallback)


def normalize_dtype(dtype: Any, fallback: str = "float32") -> str:
    if not dtype:
        return fallback
    text = str(dtype).lower()
    aliases = {
        "float": "float32",
        "fp32": "float32",
        "tensor(float)": "float32",
        "double": "float64",
        "int": "int32",
        "long": "int64",
        "tensor(int64)": "int64",
        "tensor(int32)": "int32",
        "tensor(uint8)": "uint8",
    }
    return aliases.get(text, text)


def normalize_contract(data: dict[str, Any]) -> dict[str, Any]:
    model_type = str(_first_present(data, ["model_type", "type", "profile", "model_name"], "unknown")).lower()
    model_type = model_type.replace("-", "").replace("_", "")
    if "mobilenet" in model_type:
        model_type = "mobilenetv2"
    elif "resnet" in model_type:
        model_type = "resnet18"
    elif "yolo" in model_type:
        model_type = "yolov5n"
    elif "mnist" in model_type or "lenet" in model_type:
        model_type = "mnist"

    fallback_shape = DEFAULT_SHAPES.get(model_type, [1])
    fallback_dtype = DEFAULT_DTYPES.get(model_type, "float32")
    fallback_layout = DEFAULT_LAYOUTS.get(model_type, "NCHW")

    first_input = _first_input(data)
    input_name = _first_present(data, ["input_name"], first_input.get("name") or "input")
    input_shape = normalize_shape(
        _first_present(data, ["input_shape", "shape"], first_input.get("shape")),
        fallback_shape,
    )
    input_dtype = normalize_dtype(
        _first_present(data, ["input_dtype", "dtype"], first_input.get("dtype") or first_input.get("type")),
        fallback_dtype,
    )
    input_format = str(_first_present(data, ["input_format", "layout"], first_input.get("layout") or fallback_layout)).upper()

    outputs = _first_outputs(data)
    normalized_outputs = []
    for idx, output in enumerate(outputs):
        normalized_outputs.append(
            {
                "name": output.get("name", f"output_{idx}"),
                "shape": output.get("shape"),
                "dtype": normalize_dtype(output.get("dtype") or output.get("type"), "float32"),
            }
        )

    model_file = _first_present(data, ["model_file", "model_name", "model"], "model.onnx")
    model_stem = Path(str(model_file)).stem or "model"

    return {
        "model_type": model_type,
        "model_file": str(model_file),
        "model_stem": model_stem,
        "input_name": str(input_name),
        "input_shape": input_shape,
        "input_dtype": input_dtype,
        "input_format": input_format,
        "input_shape_arg": f"{input_name}:{','.join(str(x) for x in input_shape)}",
        "outputs": normalized_outputs,
        "raw": data,
    }


def normalize_json_file(path: Path) -> dict[str, Any]:
    return normalize_contract(load_json(path))
