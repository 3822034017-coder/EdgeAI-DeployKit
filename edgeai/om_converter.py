"""JSON-driven OM converter using Ascend ATC."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from .json_contract import normalize_contract, normalize_json_file, save_json


DEFAULT_SOC = "Ascend310B4"


def _find_atc() -> Optional[str]:
    atc = shutil.which("atc")
    if atc:
        return atc

    for path in [
        "/usr/local/Ascend/ascend-toolkit/latest/bin/atc",
        "/usr/local/Ascend/ascend-toolkit/bin/atc",
    ]:
        if Path(path).exists():
            return path
    return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_model_json(model_path: Path, model_json: Optional[Path]) -> Optional[Path]:
    if model_json:
        candidate = Path(model_json).expanduser().resolve()
        return candidate if candidate.exists() else None

    candidates = [
        model_path.with_suffix(".json"),
        model_path.parent / "model.json",
        model_path.parent / "model_profile.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _infer_model_type(model_path: Path) -> str:
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


def _fallback_contract(model_path: Path, input_format: Optional[str]) -> dict[str, Any]:
    return normalize_contract(
        {
            "model_name": model_path.stem,
            "model_file": model_path.name,
            "model_type": _infer_model_type(model_path),
            "input_format": input_format or "NCHW",
        }
    )


def _parse_shape_override(raw: Optional[str], input_name: str) -> Optional[tuple[str, list[int]]]:
    if not raw:
        return None

    text = raw.strip()
    if ":" in text:
        name, shape_text = text.split(":", 1)
        resolved_name = name.strip() or input_name
    else:
        resolved_name = input_name
        shape_text = text

    shape = []
    for part in shape_text.replace("x", ",").split(","):
        part = part.strip()
        if part:
            shape.append(int(part))
    if not shape:
        return None
    return resolved_name, shape


def _read_contract(
    model_path: Path,
    model_json: Optional[Path],
    input_format: Optional[str],
    input_shape: Optional[str],
) -> tuple[dict[str, Any], Optional[Path], dict[str, Any]]:
    json_path = _resolve_model_json(model_path, model_json)
    raw: dict[str, Any]
    if json_path:
        raw = _load_json(json_path)
        contract = normalize_json_file(json_path)
    else:
        raw = {}
        contract = _fallback_contract(model_path, input_format)

    if input_format is not None:
        contract["input_format"] = str(input_format).upper()

    override = _parse_shape_override(input_shape, contract["input_name"])
    if override:
        input_name, shape = override
        contract["input_name"] = input_name
        contract["input_shape"] = shape

    contract["input_shape_arg"] = (
        f"{contract['input_name']}:{','.join(str(x) for x in contract['input_shape'])}"
    )
    return contract, json_path, raw


def _deploy_json_path(model_name: str) -> Path:
    return Path("outputs/deploy") / model_name / "deploy_result.json"


def _update_deploy_json(
    model_name: str,
    success: bool,
    error_msg: Optional[str] = None,
    om_path: Optional[Path] = None,
) -> None:
    deploy_json = _deploy_json_path(model_name)
    if not deploy_json.exists():
        return

    data = _load_json(deploy_json)
    if success:
        data["om_convert"] = "PASS"
        data["om_path"] = str(om_path) if om_path else data.get("om_path")
        data["om_error"] = None
    else:
        data["om_convert"] = "FAIL"
        data["om_error"] = error_msg
    save_json(data, deploy_json)


def _update_model_json(
    json_path: Optional[Path],
    raw: dict[str, Any],
    contract: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if not json_path:
        return

    data = dict(raw)
    data["deployment_contract"] = {key: value for key, value in contract.items() if key != "raw"}
    data.setdefault("board", {})
    data["board"]["om_convert"] = result["status"]
    data["board"]["om_path"] = result.get("om_path")
    data["board"]["om_error"] = result.get("error")
    data["board"]["atc_command"] = result.get("atc_command")
    data["input_name"] = contract["input_name"]
    data["input_shape"] = contract["input_shape"]
    data["input_format"] = contract["input_format"]
    data["input_shape_arg"] = contract["input_shape_arg"]
    save_json(data, json_path)


def build_atc_command(
    atc: str,
    model_path: Path,
    output_prefix: Path,
    soc_version: str,
    contract: dict[str, Any],
    extra_args: Optional[list[str]] = None,
) -> list[str]:
    cmd = [
        atc,
        "--framework=5",
        f"--model={model_path}",
        f"--output={output_prefix}",
        f"--soc_version={soc_version}",
        f"--input_format={contract['input_format']}",
        f"--input_shape={contract['input_shape_arg']}",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def convert_onnx_to_om(
    model_path: Path,
    output_dir: Path,
    soc_version: str = DEFAULT_SOC,
    input_format: Optional[str] = None,
    model_json: Optional[Path] = None,
    input_shape: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
    timeout: int = 600,
) -> dict[str, Any]:
    """Convert ONNX to OM with ATC.

    The converter reads the B-side JSON contract when available. Override
    input_shape only when the JSON is missing or wrong, for example:
    Input3:1,1,28,28.
    """
    model_path = Path(model_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    model_name = model_path.parent.name

    if not model_path.exists():
        error = f"Model not found: {model_path}"
        _update_deploy_json(model_name, False, "model not found")
        return {"status": "FAILED", "om_path": None, "error": error}

    atc = _find_atc()
    if not atc:
        _update_deploy_json(model_name, False, "ATC not found")
        return {"status": "ENV_MISSING", "om_path": None, "error": "ATC not found"}

    output_dir.mkdir(parents=True, exist_ok=True)
    output_prefix = output_dir / model_path.stem
    om_path = output_dir / f"{model_path.stem}.om"

    contract, json_path, raw = _read_contract(
        model_path=model_path,
        model_json=model_json,
        input_format=input_format,
        input_shape=input_shape,
    )
    cmd = build_atc_command(
        atc=atc,
        model_path=model_path,
        output_prefix=output_prefix,
        soc_version=soc_version,
        contract=contract,
        extra_args=extra_args,
    )

    print("\n[ATC COMMAND]")
    print(" ".join(cmd))

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        success = completed.returncode == 0 and om_path.exists()
        error = None if success else (completed.stderr or completed.stdout or f"ATC failed: {completed.returncode}")

        payload = {
            "status": "SUCCESS" if success else "FAILED",
            "om_path": str(om_path) if success else None,
            "error": error,
            "atc_command": " ".join(cmd),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "input_name": contract["input_name"],
            "input_shape": contract["input_shape"],
            "input_format": contract["input_format"],
        }
        _update_deploy_json(model_name, success, error, om_path if success else None)
        _update_model_json(json_path, raw, contract, payload)
        save_json(payload, output_dir / "om_convert_result.json")
        return payload

    except subprocess.TimeoutExpired:
        payload = {
            "status": "FAILED",
            "om_path": None,
            "error": "ATC timeout",
            "atc_command": " ".join(cmd),
            "input_name": contract["input_name"],
            "input_shape": contract["input_shape"],
            "input_format": contract["input_format"],
        }
        _update_deploy_json(model_name, False, payload["error"])
        _update_model_json(json_path, raw, contract, payload)
        save_json(payload, output_dir / "om_convert_result.json")
        return payload

    except Exception as exc:
        payload = {
            "status": "FAILED",
            "om_path": None,
            "error": str(exc),
            "atc_command": " ".join(cmd),
            "input_name": contract["input_name"],
            "input_shape": contract["input_shape"],
            "input_format": contract["input_format"],
        }
        _update_deploy_json(model_name, False, payload["error"])
        _update_model_json(json_path, raw, contract, payload)
        save_json(payload, output_dir / "om_convert_result.json")
        return payload
