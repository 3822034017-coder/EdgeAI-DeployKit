"""Create board-ready deployment packages.

Package output:
  model.onnx
  model.json
  input.npy
  package_result.json
  README_RUN.md
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from .input_preparer import IMAGE_SUFFIXES, create_input_npy
from .json_contract import load_json, normalize_contract, save_json
from .modelinfo import get_model_info


DEFAULT_OUTPUT_ROOT = Path("outputs/packages")


def _infer_model_type(model_path: Path, explicit_type: Optional[str] = None) -> str:
    if explicit_type:
        return explicit_type.lower()

    text = f"{model_path.parent.name} {model_path.stem}".lower().replace("-", "").replace("_", "")
    if "mnist" in text or "lenet" in text:
        return "mnist"
    if "mobilenet" in text:
        return "mobilenetv2"
    if "resnet" in text:
        return "resnet18"
    if "yolo" in text:
        return "yolov5n"
    return model_path.parent.name.lower()


def _fallback_json(model_path: Path, model_type: str) -> dict[str, Any]:
    data = get_model_info(model_path)
    data["model_name"] = model_path.stem
    data["model_file"] = "model.onnx"
    data["model_type"] = model_type
    data["onnx_path"] = "model.onnx"
    data["input_dtype"] = "float32"
    data["input_format"] = "NCHW"
    data["board"] = {"status": "pending"}
    return data


def _write_readme(output_dir: Path, contract: dict[str, Any]) -> None:
    readme = f"""# EdgeAI Deploy Package

Model type: `{contract["model_type"]}`
Input: `{contract["input_shape_arg"]}`
Input dtype: `{contract["input_dtype"]}`
Input format: `{contract["input_format"]}`

## Board run

```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
python3 convert.py --dir .
airloader -m model.om -p 7891
python3 run_model.py --json model.json --input input.npy -r 127.0.0.1 -p 7891 -o board_result.json --update-json
```
"""
    (output_dir / "README_RUN.md").write_text(readme, encoding="utf-8")


def _public_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in contract.items() if key != "raw"}


def _copy_source_image(input_path: Optional[Path], output_dir: Path) -> Optional[str]:
    if not input_path:
        return None
    if input_path.suffix.lower() not in IMAGE_SUFFIXES:
        return None
    target_name = f"source_image{input_path.suffix.lower()}"
    shutil.copy2(input_path, output_dir / target_name)
    return target_name


def package_model(
    model_path: Path,
    model_type: Optional[str] = None,
    output_dir: Optional[Path] = None,
    input_path: Optional[Path] = None,
    model_json: Optional[Path] = None,
    builtin_input: bool = False,
) -> Path:
    """Create a deploy package for board-sync.

    Args:
        model_path: ONNX model path.
        model_type: mnist/mobilenetv2/resnet18/yolov5n. If omitted, infer from path.
        output_dir: target package dir. If omitted, outputs/packages/<model_type>.
        input_path: optional user image/file for input.npy generation.
        model_json: optional B-side JSON. If omitted, modelinfo.py is used.
        builtin_input: generate dummy input when no input_path is provided.
    """

    model_path = Path(model_path).expanduser().resolve()
    if not model_path.exists():
        raise FileNotFoundError(f"model not found: {model_path}")
    if model_path.suffix.lower() != ".onnx":
        raise ValueError(f"expected .onnx model, got: {model_path}")
    if not input_path and not builtin_input:
        raise ValueError("--input is required when --no-builtin-input is used")

    resolved_type = _infer_model_type(model_path, model_type)
    output_dir = Path(output_dir or (DEFAULT_OUTPUT_ROOT / resolved_type)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    target_model = output_dir / "model.onnx"
    target_json = output_dir / "model.json"
    target_input = output_dir / "input.npy"
    source_input = Path(input_path).expanduser().resolve() if input_path else None
    source_image_file = _copy_source_image(source_input, output_dir)

    shutil.copy2(model_path, target_model)

    if model_json:
        raw = load_json(Path(model_json).expanduser().resolve())
        raw.setdefault("model_name", model_path.stem)
        raw.setdefault("original_model_file", raw.get("model_file") or raw.get("model") or model_path.name)
        raw["model_file"] = "model.onnx"
        raw["model_type"] = resolved_type
        raw["onnx_path"] = "model.onnx"
    else:
        raw = _fallback_json(target_model, resolved_type)

    contract = normalize_contract(raw)
    raw["deployment_contract"] = _public_contract(contract)
    raw["input_source"] = {
        "mode": "file" if input_path else "builtin",
        "file": "input.npy",
        "source": str(source_input) if source_input else None,
        "source_file": source_image_file,
    }
    raw.setdefault("board", {"status": "pending"})
    save_json(raw, target_json)

    create_input_npy(
        json_path=target_json,
        output_path=target_input,
        image_path=source_input,
        dummy_mode="zeros" if builtin_input or not input_path else "zeros",
    )

    files = ["model.onnx", "model.json", "input.npy"]
    if source_image_file:
        files.append(source_image_file)

    package_result = {
        "status": "success",
        "package": "PASS",
        "package_dir": str(output_dir),
        "model_type": contract["model_type"],
        "input_name": contract["input_name"],
        "input_shape": contract["input_shape"],
        "input_dtype": contract["input_dtype"],
        "input_format": contract["input_format"],
        "files": files,
    }
    save_json(package_result, output_dir / "package_result.json")
    _write_readme(output_dir, contract)

    print(f"Deploy package generated: {output_dir}")
    print(f"[OK] input.npy shape={contract['input_shape']} dtype={contract['input_dtype']}")
    return output_dir


def generate_package(model_path):
    """Backward-compatible wrapper used by the old CLI."""
    return package_model(
        model_path=Path(model_path),
        model_type=None,
        output_dir=None,
        input_path=None,
        model_json=None,
        builtin_input=True,
    )
