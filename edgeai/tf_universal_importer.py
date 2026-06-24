from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _import_tensorflow():
    try:
        import tensorflow as tf  # type: ignore
        return tf
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "TensorFlow importer requires tensorflow. Install with: python -m pip install tensorflow-cpu tf2onnx"
        ) from exc


def _import_h5py():
    try:
        import h5py  # type: ignore
        return h5py
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Keras H5 importer requires h5py. Install with: python -m pip install h5py") from exc


def _run(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or Path.cwd()),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout or ""


def _shape_to_list(shape: Any) -> Optional[List[Any]]:
    try:
        if shape is None:
            return None
        if hasattr(shape, "as_list"):
            return [None if x is None else int(x) for x in shape.as_list()]
        if isinstance(shape, (list, tuple)):
            return [None if x is None else int(x) for x in shape]
    except Exception:
        return None
    return None


def _parse_shape_text(shape: str | None) -> Optional[List[int]]:
    if not shape:
        return None
    text = str(shape).strip().lower().replace("×", "x").replace(" ", "")
    if not text:
        return None
    if ";" in text:
        text = text.split(";", 1)[0]
    if ":" in text:
        text = text.split(":", 1)[1]
    text = text.replace("x", ",")
    out: List[int] = []
    for part in text.split(","):
        if not part:
            continue
        if part in {"?", "-1", "none", "dynamic", "batch", "n"}:
            out.append(1)
        else:
            out.append(int(part))
    return out or None


def _infer_task_type_from_shapes(inputs: List[Dict[str, Any]], outputs: List[Dict[str, Any]]) -> Optional[str]:
    if not outputs:
        return None
    shape = outputs[0].get("shape") or []
    numeric = [x for x in shape if isinstance(x, int)]
    if len(numeric) >= 1:
        last = numeric[-1]
        if last == 10:
            return "digit_classification"
        if last == 1000:
            return "image_classification"
    if len(shape) == 3:
        last = shape[-1]
        if isinstance(last, int) and last in {84, 85, 86}:
            return "object_detection"
    if len(shape) == 4:
        return "segmentation_or_image_output"
    return None


def detect_tensorflow_kind(source: str | Path) -> str:
    src = Path(source)
    if src.is_dir():
        if (src / "saved_model.pb").exists():
            return "saved_model"
        if (src / "checkpoint").exists() or list(src.glob("*.index")):
            return "tensorflow_checkpoint"
        return "tensorflow_directory_unknown"
    suffix = src.suffix.lower()
    if suffix == ".keras":
        return "keras_v3"
    if suffix in {".h5", ".hdf5"}:
        return "keras_h5"
    if suffix == ".pb":
        return "graphdef_pb"
    if suffix == ".tflite":
        return "tflite"
    if suffix in {".ckpt", ".index"}:
        return "tensorflow_checkpoint"
    return "tensorflow_unknown"


def _keras_shape_to_signature_shape(shape: Any, fallback_input_shape: str | None = None) -> List[int]:
    parsed = _parse_shape_text(fallback_input_shape)
    if parsed:
        return parsed
    shape_list = _shape_to_list(shape) or []
    # Keras model.input_shape usually includes batch; export concrete signature should too.
    out: List[int] = []
    for i, dim in enumerate(shape_list):
        if dim is None:
            out.append(1 if i == 0 else 1)
        else:
            out.append(int(dim))
    if not out:
        out = [1, 28, 28, 1]
    return out


def _load_keras_model_normal(source: Path):
    tf = _import_tensorflow()
    return tf.keras.models.load_model(str(source), compile=False)


def _extract_h5_attr_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    if hasattr(value, "tobytes"):
        return value.tobytes().decode("utf-8")
    return str(value)


def _normalize_legacy_input_shape(value: Any, fallback_input_shape: str | None = None) -> Optional[Tuple[int, ...]]:
    parsed = _parse_shape_text(fallback_input_shape)
    if parsed and len(parsed) >= 2:
        return tuple(parsed[1:])
    if not isinstance(value, (list, tuple)):
        return None
    arr = list(value)
    # Old Keras sometimes stores batch_input_shape=[None, 28, 28, 1].
    # Keras 3 may interpret input_shape=[None, 28, 28, 1] as per-sample shape,
    # causing a bogus 5D input. Drop leading batch/dynamic None values until rank is sane.
    while len(arr) > 1 and arr[0] is None:
        arr = arr[1:]
    if len(arr) in {1, 2, 3, 4}:
        return tuple(int(x) if x is not None else 1 for x in arr)
    return None


def _make_keras_layer(layer_spec: Dict[str, Any]):
    tf = _import_tensorflow()
    from tensorflow import keras  # type: ignore
    from tensorflow.keras import layers  # type: ignore

    class_name = str(layer_spec.get("class_name") or "")
    cfg = dict(layer_spec.get("config") or {})
    name = cfg.get("name")

    def common() -> Dict[str, Any]:
        return {"name": name} if name else {}

    if class_name in {"InputLayer"}:
        return None

    if class_name == "Conv2D":
        return layers.Conv2D(
            filters=int(cfg.get("filters")),
            kernel_size=tuple(cfg.get("kernel_size") or (3, 3)),
            strides=tuple(cfg.get("strides") or (1, 1)),
            padding=str(cfg.get("padding") or "valid"),
            dilation_rate=tuple(cfg.get("dilation_rate") or (1, 1)),
            activation=cfg.get("activation"),
            use_bias=bool(cfg.get("use_bias", True)),
            data_format=cfg.get("data_format") or None,
            **common(),
        )
    if class_name == "SeparableConv2D":
        return layers.SeparableConv2D(
            filters=int(cfg.get("filters")),
            kernel_size=tuple(cfg.get("kernel_size") or (3, 3)),
            strides=tuple(cfg.get("strides") or (1, 1)),
            padding=str(cfg.get("padding") or "valid"),
            activation=cfg.get("activation"),
            use_bias=bool(cfg.get("use_bias", True)),
            data_format=cfg.get("data_format") or None,
            **common(),
        )
    if class_name == "DepthwiseConv2D":
        return layers.DepthwiseConv2D(
            kernel_size=tuple(cfg.get("kernel_size") or (3, 3)),
            strides=tuple(cfg.get("strides") or (1, 1)),
            padding=str(cfg.get("padding") or "valid"),
            activation=cfg.get("activation"),
            use_bias=bool(cfg.get("use_bias", True)),
            data_format=cfg.get("data_format") or None,
            **common(),
        )
    if class_name in {"MaxPooling2D", "MaxPool2D"}:
        return layers.MaxPooling2D(
            pool_size=tuple(cfg.get("pool_size") or (2, 2)),
            strides=None if cfg.get("strides") is None else tuple(cfg.get("strides")),
            padding=str(cfg.get("padding") or "valid"),
            data_format=cfg.get("data_format") or None,
            **common(),
        )
    if class_name == "AveragePooling2D":
        return layers.AveragePooling2D(
            pool_size=tuple(cfg.get("pool_size") or (2, 2)),
            strides=None if cfg.get("strides") is None else tuple(cfg.get("strides")),
            padding=str(cfg.get("padding") or "valid"),
            data_format=cfg.get("data_format") or None,
            **common(),
        )
    if class_name == "GlobalAveragePooling2D":
        return layers.GlobalAveragePooling2D(data_format=cfg.get("data_format") or None, **common())
    if class_name == "GlobalMaxPooling2D":
        return layers.GlobalMaxPooling2D(data_format=cfg.get("data_format") or None, **common())
    if class_name == "Dropout":
        return layers.Dropout(rate=float(cfg.get("rate", 0.5)), **common())
    if class_name == "Flatten":
        return layers.Flatten(data_format=cfg.get("data_format") or None, **common())
    if class_name == "Dense":
        return layers.Dense(
            units=int(cfg.get("units")),
            activation=cfg.get("activation"),
            use_bias=bool(cfg.get("use_bias", True)),
            **common(),
        )
    if class_name == "BatchNormalization":
        return layers.BatchNormalization(
            axis=cfg.get("axis", -1),
            momentum=float(cfg.get("momentum", 0.99)),
            epsilon=float(cfg.get("epsilon", 0.001)),
            center=bool(cfg.get("center", True)),
            scale=bool(cfg.get("scale", True)),
            **common(),
        )
    if class_name == "Activation":
        return layers.Activation(cfg.get("activation"), **common())
    if class_name == "ReLU":
        return layers.ReLU(**common())
    if class_name == "Rescaling":
        return layers.Rescaling(scale=cfg.get("scale", 1.0), offset=cfg.get("offset", 0.0), **common())
    if class_name == "Reshape":
        return layers.Reshape(target_shape=tuple(cfg.get("target_shape")), **common())
    if class_name == "Permute":
        return layers.Permute(dims=tuple(cfg.get("dims")), **common())
    if class_name == "ZeroPadding2D":
        return layers.ZeroPadding2D(padding=cfg.get("padding", ((1, 1), (1, 1))), data_format=cfg.get("data_format") or None, **common())

    raise RuntimeError(
        f"unsupported legacy Keras layer {class_name!r}. "
        "Provide a modern .keras/SavedModel export, or add this layer to edgeai/tf_universal_importer.py."
    )


def _read_h5_weights(layer_group: Any) -> List[Any]:
    import numpy as np  # type: ignore

    names = layer_group.attrs.get("weight_names", [])
    out: List[Any] = []
    for raw_name in names:
        name = raw_name.decode("utf-8") if isinstance(raw_name, bytes) else str(raw_name)
        if name in layer_group:
            out.append(np.array(layer_group[name]))
            continue
        cur = layer_group
        ok = True
        for part in name.split("/"):
            if part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and hasattr(cur, "shape"):
            out.append(np.array(cur))
            continue
        # Last-resort search by dataset suffix.
        found = None
        suffix = "/" + name.split("/")[-1]

        def visit(_, obj):
            nonlocal found
            if found is not None:
                return
            if hasattr(obj, "shape") and str(obj.name).endswith(suffix):
                found = np.array(obj)

        layer_group.visititems(visit)
        if found is None:
            raise KeyError(f"cannot find weight dataset: {name}")
        out.append(found)
    return out


def _build_legacy_h5_keras_model(source: Path, input_shape: str | None = None):
    """Rebuild a broad class of old Sequential H5 files without trusting old input_shape parsing.

    This is a generic fallback for legacy Keras H5 files. It reads model_config,
    recreates supported Keras layers, then loads weights by layer name. It is not
    tied to MNIST; unsupported custom layers fail with a clear message.
    """
    tf = _import_tensorflow()
    from tensorflow import keras  # type: ignore

    h5py = _import_h5py()
    with h5py.File(source, "r") as f:
        raw = f.attrs.get("model_config")
        if raw is None:
            raise RuntimeError("legacy H5 has no model_config; it may contain weights only, not a complete model")
        config = json.loads(_extract_h5_attr_text(raw))
        class_name = config.get("class_name")
        if class_name != "Sequential":
            raise RuntimeError(
                f"legacy H5 fallback currently supports Sequential configs; found {class_name!r}. "
                "Use a modern .keras or SavedModel export for functional/custom models."
            )
        layer_specs = list(config.get("config", {}).get("layers", []))
        if not layer_specs:
            raise RuntimeError("legacy H5 model_config contains no layers")

        first_shape = None
        for layer_spec in layer_specs:
            cfg = layer_spec.get("config", {}) or {}
            for key in ("batch_input_shape", "batch_shape", "input_shape"):
                if key in cfg:
                    first_shape = _normalize_legacy_input_shape(cfg.get(key), input_shape)
                    if first_shape:
                        break
            if first_shape:
                break
        if not first_shape:
            parsed = _parse_shape_text(input_shape)
            if parsed and len(parsed) >= 2:
                first_shape = tuple(parsed[1:])
        if not first_shape:
            raise RuntimeError("could not infer Keras input shape; provide --input-shape, e.g. 1,28,28,1")

        model = keras.Sequential(name=(config.get("config", {}) or {}).get("name") or "edgeai_legacy_h5")
        model.add(keras.Input(shape=first_shape, name="input"))
        for layer_spec in layer_specs:
            layer = _make_keras_layer(layer_spec)
            if layer is not None:
                model.add(layer)

        # Build once before loading weights.
        dummy_shape = [1] + [1 if x is None else int(x) for x in first_shape]
        model(tf.zeros(dummy_shape, dtype=tf.float32))

        mw = f.get("model_weights")
        if mw is None:
            raise RuntimeError("legacy H5 has no model_weights group")
        loaded: List[str] = []
        for layer in model.layers:
            if layer.name in mw:
                weights = _read_h5_weights(mw[layer.name])
                if weights:
                    try:
                        layer.set_weights(weights)
                        loaded.append(layer.name)
                    except Exception as exc:
                        raise RuntimeError(
                            f"failed to load weights for layer {layer.name!r}: {exc}. "
                            "The H5 config and weights may not match the supported generic reconstruction path."
                        ) from exc
        model._edgeai_loaded_layers = loaded  # type: ignore[attr-defined]
        return model


def load_keras_model_universal(source: str | Path, input_shape: str | None = None):
    src = Path(source)
    try:
        model = _load_keras_model_normal(src)
        model._edgeai_load_method = "keras_load_model"  # type: ignore[attr-defined]
        return model
    except Exception as normal_exc:
        if src.suffix.lower() not in {".h5", ".hdf5"}:
            raise
        try:
            model = _build_legacy_h5_keras_model(src, input_shape=input_shape)
            model._edgeai_load_method = "legacy_h5_rebuild"  # type: ignore[attr-defined]
            model._edgeai_original_load_error = repr(normal_exc)  # type: ignore[attr-defined]
            return model
        except Exception as fallback_exc:
            raise RuntimeError(
                "failed to load Keras H5 with both standard loader and generic legacy fallback.\n"
                f"standard loader error: {type(normal_exc).__name__}: {normal_exc}\n"
                f"legacy fallback error: {type(fallback_exc).__name__}: {fallback_exc}"
            ) from fallback_exc


def _export_keras_to_saved_model(model: Any, export_dir: Path) -> None:
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(model, "export"):
        model.export(str(export_dir))
    else:
        tf = _import_tensorflow()
        tf.saved_model.save(model, str(export_dir))


def _probe_keras(source: Path, input_shape: str | None = None) -> Dict[str, Any]:
    model = load_keras_model_universal(source, input_shape=input_shape)
    inputs = [{"name": getattr(i, "name", "input"), "shape": _shape_to_list(getattr(i, "shape", None))} for i in getattr(model, "inputs", [])]
    outputs = [{"name": getattr(o, "name", "output"), "shape": _shape_to_list(getattr(o, "shape", None))} for o in getattr(model, "outputs", [])]
    return {
        "ok": True,
        "kind": detect_tensorflow_kind(source),
        "load_method": getattr(model, "_edgeai_load_method", "keras_load_model"),
        "input_shape": _shape_to_list(getattr(model, "input_shape", None)),
        "output_shape": _shape_to_list(getattr(model, "output_shape", None)),
        "inputs": inputs,
        "outputs": outputs,
        "task_type": _infer_task_type_from_shapes(inputs, outputs),
        "loaded_weight_layers": getattr(model, "_edgeai_loaded_layers", None),
        "standard_load_error": getattr(model, "_edgeai_original_load_error", None),
    }


def _probe_saved_model(source: Path) -> Dict[str, Any]:
    tf = _import_tensorflow()
    obj = tf.saved_model.load(str(source))
    signatures = getattr(obj, "signatures", {}) or {}
    items = []
    for name, fn in signatures.items():
        in_items = []
        out_items = []
        try:
            for k, spec in (fn.structured_input_signature[1] or {}).items():
                in_items.append({"name": str(k), "shape": _shape_to_list(getattr(spec, "shape", None)), "dtype": str(getattr(spec, "dtype", ""))})
        except Exception:
            pass
        try:
            outputs = fn.structured_outputs or {}
            if isinstance(outputs, dict):
                for k, spec in outputs.items():
                    out_items.append({"name": str(k), "shape": _shape_to_list(getattr(spec, "shape", None)), "dtype": str(getattr(spec, "dtype", ""))})
        except Exception:
            pass
        items.append({"name": str(name), "inputs": in_items, "outputs": out_items})
    first_inputs = items[0]["inputs"] if items else []
    first_outputs = items[0]["outputs"] if items else []
    return {
        "ok": True,
        "kind": "saved_model",
        "signatures": items,
        "inputs": first_inputs,
        "outputs": first_outputs,
        "task_type": _infer_task_type_from_shapes(first_inputs, first_outputs),
    }


def _probe_graphdef(source: Path) -> Dict[str, Any]:
    tf = _import_tensorflow()
    graph_def = tf.compat.v1.GraphDef()
    graph_def.ParseFromString(source.read_bytes())
    nodes = list(graph_def.node)
    consumers: Dict[str, int] = {}
    for n in nodes:
        for inp in n.input:
            base = inp.lstrip("^").split(":", 1)[0]
            consumers[base] = consumers.get(base, 0) + 1
    inputs = []
    outputs = []
    for n in nodes:
        if n.op == "Placeholder":
            shape = []
            try:
                shp = n.attr.get("shape")
                if shp:
                    for d in shp.shape.dim:
                        shape.append(None if d.size < 0 else int(d.size))
            except Exception:
                pass
            inputs.append({"name": n.name + ":0", "shape": shape})
    for n in nodes:
        if consumers.get(n.name, 0) == 0 and n.op not in {"Const", "NoOp", "Placeholder"}:
            outputs.append({"name": n.name + ":0", "op": n.op})
    return {"ok": True, "kind": "graphdef_pb", "inputs": inputs, "outputs": outputs[:20], "node_count": len(nodes)}


def _probe_tflite(source: Path) -> Dict[str, Any]:
    tf = _import_tensorflow()
    interpreter = tf.lite.Interpreter(model_path=str(source))
    interpreter.allocate_tensors()
    inputs = []
    outputs = []
    for d in interpreter.get_input_details():
        inputs.append({"name": d.get("name"), "shape": list(d.get("shape", [])), "dtype": str(d.get("dtype"))})
    for d in interpreter.get_output_details():
        outputs.append({"name": d.get("name"), "shape": list(d.get("shape", [])), "dtype": str(d.get("dtype"))})
    return {"ok": True, "kind": "tflite", "inputs": inputs, "outputs": outputs, "task_type": _infer_task_type_from_shapes(inputs, outputs)}


def probe_tensorflow_model(source: str | Path, input_shape: str | None = None) -> Dict[str, Any]:
    src = Path(source)
    kind = detect_tensorflow_kind(src)
    if kind in {"keras_v3", "keras_h5"}:
        return _probe_keras(src, input_shape=input_shape)
    if kind == "saved_model":
        return _probe_saved_model(src)
    if kind == "graphdef_pb":
        return _probe_graphdef(src)
    if kind == "tflite":
        return _probe_tflite(src)
    if kind == "tensorflow_checkpoint":
        return {
            "ok": False,
            "kind": kind,
            "requires_input": True,
            "message": "TensorFlow checkpoints usually contain variables only. Please provide a SavedModel, .keras/.h5 model, or frozen .pb graph.",
        }
    return {"ok": False, "kind": kind, "message": f"unsupported TensorFlow model container: {src}"}


def convert_tensorflow_universal(
    source: str | Path,
    output_onnx: str | Path,
    opset: int = 15,
    input_name: str | None = None,
    output_name: str | None = None,
    input_shape: str | None = None,
) -> Dict[str, Any]:
    try:
        import tf2onnx  # noqa: F401  # type: ignore
    except Exception as exc:
        raise RuntimeError("TensorFlow conversion requires tf2onnx. Install with: python -m pip install tensorflow-cpu tf2onnx") from exc

    src = Path(source)
    out = Path(output_onnx)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    kind = detect_tensorflow_kind(src)
    info: Dict[str, Any] = {"kind": kind, "opset": opset, "source_model": str(src), "output_onnx": str(out)}

    if kind in {"keras_v3", "keras_h5"}:
        model = load_keras_model_universal(src, input_shape=input_shape)
        info["load_method"] = getattr(model, "_edgeai_load_method", "keras_load_model")
        info["input_shape"] = _shape_to_list(getattr(model, "input_shape", None))
        info["output_shape"] = _shape_to_list(getattr(model, "output_shape", None))
        if getattr(model, "_edgeai_original_load_error", None):
            info["standard_load_error"] = getattr(model, "_edgeai_original_load_error")
        if getattr(model, "_edgeai_loaded_layers", None):
            info["loaded_weight_layers"] = getattr(model, "_edgeai_loaded_layers")

        with tempfile.TemporaryDirectory(prefix="edgeai_tf_export_") as tmp:
            export_dir = Path(tmp) / "saved_model"
            _export_keras_to_saved_model(model, export_dir)
            cmd = [sys.executable, "-m", "tf2onnx.convert", "--saved-model", str(export_dir), "--output", str(out), "--opset", str(opset)]
            code, text = _run(cmd)
            info["tf2onnx_command"] = " ".join(cmd)
            if code != 0 or not out.exists():
                raise RuntimeError("tf2onnx Keras/SavedModel conversion failed:\n" + text[-8000:])
            info["tf2onnx_output_tail"] = text[-2000:]

    elif kind == "saved_model":
        cmd = [sys.executable, "-m", "tf2onnx.convert", "--saved-model", str(src), "--output", str(out), "--opset", str(opset)]
        code, text = _run(cmd)
        info["tf2onnx_command"] = " ".join(cmd)
        if code != 0 or not out.exists():
            raise RuntimeError("tf2onnx SavedModel conversion failed:\n" + text[-8000:])
        info["tf2onnx_output_tail"] = text[-2000:]

    elif kind == "graphdef_pb":
        if not input_name or input_name == "input" or not output_name or output_name == "output":
            probe = _probe_graphdef(src)
            in_hint = ", ".join(x.get("name", "") for x in probe.get("inputs", [])[:5]) or "<unknown>"
            out_hint = ", ".join(x.get("name", "") for x in probe.get("outputs", [])[:5]) or "<unknown>"
            raise RuntimeError(
                "Frozen GraphDef .pb conversion requires --input-name and --output-name node names, usually with :0 suffix.\n"
                f"Input candidates: {in_hint}\nOutput candidates: {out_hint}"
            )
        cmd = [
            sys.executable,
            "-m",
            "tf2onnx.convert",
            "--graphdef",
            str(src),
            "--inputs",
            input_name,
            "--outputs",
            output_name,
            "--output",
            str(out),
            "--opset",
            str(opset),
        ]
        code, text = _run(cmd)
        info["tf2onnx_command"] = " ".join(cmd)
        if code != 0 or not out.exists():
            raise RuntimeError("tf2onnx GraphDef conversion failed:\n" + text[-8000:])
        info["tf2onnx_output_tail"] = text[-2000:]

    elif kind == "tflite":
        # tf2onnx supports TFLite conversion for many models. Keep this generic;
        # unsupported ops will be reported by tf2onnx with concrete missing op names.
        cmd = [sys.executable, "-m", "tf2onnx.convert", "--tflite", str(src), "--output", str(out), "--opset", str(opset)]
        code, text = _run(cmd)
        info["tf2onnx_command"] = " ".join(cmd)
        if code != 0 or not out.exists():
            raise RuntimeError("tf2onnx TFLite conversion failed:\n" + text[-8000:])
        info["tf2onnx_output_tail"] = text[-2000:]

    elif kind == "tensorflow_checkpoint":
        raise RuntimeError(
            "TensorFlow checkpoint files usually contain variables only and cannot be converted without a graph/model definition. "
            "Export the model as SavedModel or .keras first."
        )
    else:
        raise RuntimeError(f"unsupported TensorFlow source kind {kind!r}: {src}")

    info["ok"] = True
    return info
