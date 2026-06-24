from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_PACKAGE_ROOT = Path("outputs/packages")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_name(name: str) -> str:
    name = (name or "").strip().replace("\\", "/").split("/")[-1]
    keep = []
    for ch in name:
        if ch.isalnum() or ch in ("_", "-", "."):
            keep.append(ch)
        else:
            keep.append("_")
    out = "".join(keep).strip("._")
    if not out:
        raise ValueError("model name is empty")
    return out


@dataclass(frozen=True)
class PackagePaths:
    root: Path
    source_model_dir: Path
    model_onnx: Path
    model_json: Path
    model_signature_json: Path
    operator_report_json: Path
    preprocess_json: Path
    label_map_json: Path
    source_input: Path
    input_npy: Path
    local_output_npy: Path
    local_result_json: Path


def package_paths(package_dir: Path) -> PackagePaths:
    package_dir = Path(package_dir)
    return PackagePaths(
        root=package_dir,
        source_model_dir=package_dir / "source_model",
        model_onnx=package_dir / "model.onnx",
        model_json=package_dir / "model.json",
        model_signature_json=package_dir / "model_signature.json",
        operator_report_json=package_dir / "operator_report.json",
        preprocess_json=package_dir / "preprocess.json",
        label_map_json=package_dir / "label_map.json",
        source_input=package_dir / "source_input",
        input_npy=package_dir / "input.npy",
        local_output_npy=package_dir / "local_output.npy",
        local_result_json=package_dir / "local_result.json",
    )


def _copy_source_model(source: Path, dst_dir: Path, overwrite: bool = False) -> Path:
    source = Path(source)
    dst_dir.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise FileNotFoundError(f"source model not found: {source}")

    if source.is_dir():
        target = dst_dir / source.name
        if target.exists():
            if not overwrite:
                return target
            shutil.rmtree(target)
        shutil.copytree(source, target)
        return target

    target = dst_dir / source.name
    if target.exists() and overwrite:
        target.unlink()
    if not target.exists():
        shutil.copy2(source, target)
    return target


def init_package(
    name: str,
    source_model: Path,
    framework: str = "onnx",
    output_root: Path = DEFAULT_PACKAGE_ROOT,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Create a standard EdgeAI user-model package.

    First version supports framework=onnx as the full working path. Other frameworks
    can still be recorded and copied, then converted by future converter commands.
    """
    model_name = _safe_name(name)
    framework = (framework or "onnx").lower().strip()
    source_model = Path(source_model)
    output_root = Path(output_root)
    package_dir = output_root / model_name
    paths = package_paths(package_dir)

    if package_dir.exists() and overwrite:
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    paths.source_model_dir.mkdir(parents=True, exist_ok=True)

    copied_source = _copy_source_model(source_model, paths.source_model_dir, overwrite=overwrite)

    onnx_created = False
    if framework == "onnx":
        if source_model.is_file():
            if source_model.suffix.lower() != ".onnx":
                raise ValueError("framework=onnx requires a .onnx file")
            if paths.model_onnx.exists() and overwrite:
                paths.model_onnx.unlink()
            if not paths.model_onnx.exists():
                shutil.copy2(source_model, paths.model_onnx)
            onnx_created = True
        elif source_model.is_dir():
            candidates = list(source_model.rglob("*.onnx"))
            if not candidates:
                raise ValueError(f"no .onnx file found in source directory: {source_model}")
            chosen = candidates[0]
            if paths.model_onnx.exists() and overwrite:
                paths.model_onnx.unlink()
            if not paths.model_onnx.exists():
                shutil.copy2(chosen, paths.model_onnx)
            onnx_created = True

    meta = {
        "model_name": model_name,
        "framework": framework,
        "package_dir": str(package_dir),
        "source_model": str(source_model),
        "copied_source": str(copied_source),
        "onnx_path": str(paths.model_onnx) if paths.model_onnx.exists() else None,
        "onnx_ready": paths.model_onnx.exists(),
        "created_at": _now_iso(),
        "stage": "init-package",
        "notes": "framework=onnx copies the model directly; other frameworks need edgeai convert in later patches.",
    }
    paths.model_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "ok": True,
        "package_dir": str(package_dir),
        "model_name": model_name,
        "framework": framework,
        "model_json": str(paths.model_json),
        "model_onnx": str(paths.model_onnx) if paths.model_onnx.exists() else None,
        "onnx_created": onnx_created,
    }


def load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
