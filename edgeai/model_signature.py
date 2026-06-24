from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from .package_layout import package_paths, save_json


def _dtype_name(elem_type: int) -> str:
    try:
        import onnx
        return onnx.TensorProto.DataType.Name(elem_type).lower()
    except Exception:
        return str(elem_type)


def _value_info_to_dict(value_info: Any) -> Dict[str, Any]:
    tensor_type = value_info.type.tensor_type
    elem_type = int(tensor_type.elem_type)
    shape: List[Optional[Any]] = []
    dynamic = False
    for dim in tensor_type.shape.dim:
        if dim.dim_value > 0:
            shape.append(int(dim.dim_value))
        elif dim.dim_param:
            shape.append(str(dim.dim_param))
            dynamic = True
        else:
            shape.append(None)
            dynamic = True

    return {
        "name": value_info.name,
        "shape": shape,
        "dtype": _dtype_name(elem_type),
        "dynamic": dynamic,
        "layout_guess": guess_layout(shape),
    }


def guess_layout(shape: List[Optional[Any]]) -> str:
    if len(shape) != 4:
        return "unknown"
    c1 = shape[1]
    c_last = shape[-1]
    if isinstance(c1, int) and c1 in (1, 3, 4):
        return "NCHW"
    if isinstance(c_last, int) and c_last in (1, 3, 4):
        return "NHWC"
    return "unknown"


def analyze_onnx_model(model_path: Path) -> Dict[str, Any]:
    try:
        import onnx
    except ImportError as exc:
        raise RuntimeError("需要安装 onnx: pip install onnx") from exc

    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"model not found: {model_path}")

    model = onnx.load(str(model_path))
    onnx.checker.check_model(model)

    initializers = {init.name for init in model.graph.initializer}
    inputs = [
        _value_info_to_dict(inp)
        for inp in model.graph.input
        if inp.name not in initializers
    ]
    outputs = [_value_info_to_dict(out) for out in model.graph.output]
    op_counter = Counter(node.op_type for node in model.graph.node)
    opset = [
        {"domain": item.domain or "ai.onnx", "version": int(item.version)}
        for item in model.opset_import
    ]

    return {
        "model_path": str(model_path),
        "ir_version": int(model.ir_version),
        "producer_name": model.producer_name,
        "producer_version": model.producer_version,
        "opset": opset,
        "inputs": inputs,
        "outputs": outputs,
        "node_count": len(model.graph.node),
        "operator_count": dict(sorted(op_counter.items(), key=lambda x: (-x[1], x[0]))),
        "has_dynamic_shape": any(x.get("dynamic") for x in inputs + outputs),
    }


def analyze_package(package_dir: Path) -> Dict[str, Any]:
    paths = package_paths(Path(package_dir))
    if not paths.model_onnx.exists():
        raise FileNotFoundError(f"model.onnx not found in package: {paths.root}")

    signature = analyze_onnx_model(paths.model_onnx)
    save_json(paths.model_signature_json, signature)

    operator_report = {
        "model_path": str(paths.model_onnx),
        "node_count": signature["node_count"],
        "operator_count": signature["operator_count"],
    }
    save_json(paths.operator_report_json, operator_report)

    return {
        "ok": True,
        "package_dir": str(paths.root),
        "model_signature": str(paths.model_signature_json),
        "operator_report": str(paths.operator_report_json),
        "inputs": signature["inputs"],
        "outputs": signature["outputs"],
        "opset": signature["opset"],
        "has_dynamic_shape": signature["has_dynamic_shape"],
    }
