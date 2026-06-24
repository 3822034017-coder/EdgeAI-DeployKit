from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from backend.schemas import ModelItem
from backend.services.paths import INPUTS_DIR, PROJECT_ROOT, rel
from backend.services.security import safe_filename


def infer_type(path: str) -> str:
    lower = path.lower()
    if "mnist" in lower:
        return "mnist"
    if "mobilenet" in lower:
        return "mobilenetv2"
    if "resnet" in lower:
        return "resnet18"
    if "yolo" in lower:
        return "yolov5n"
    return "auto"


def source_for(path: Path) -> str:
    text = rel(path)
    if text.startswith("models/"):
        return "zoo"
    if text.startswith("examples/"):
        return "example"
    if text.startswith("inputs/"):
        return "upload"
    if text.startswith("outputs/"):
        return "output"
    return "custom"


def list_models() -> list[ModelItem]:
    patterns = ["models/**/*.onnx", "examples/**/*.onnx", "inputs/**/*.onnx", "outputs/**/*.onnx"]
    seen: set[str] = set()
    items: list[ModelItem] = []
    for pattern in patterns:
        for path in PROJECT_ROOT.glob(pattern):
            if not path.is_file():
                continue
            rp = rel(path)
            if rp in seen:
                continue
            seen.add(rp)
            stat = path.stat()
            items.append(ModelItem(
                name=path.stem,
                path=rp,
                type=infer_type(rp),
                size_mb=round(stat.st_size / 1024 / 1024, 4),
                source=source_for(path),
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            ))
    return sorted(items, key=lambda item: (item.source, item.name))


def save_upload(kind: str, file: UploadFile) -> str:
    subdir = {"model": "models", "image": "images", "input": "inputs", "json": "json"}[kind]
    folder = INPUTS_DIR / subdir
    folder.mkdir(parents=True, exist_ok=True)
    name = safe_filename(file.filename or "upload.bin")
    target = folder / name
    with target.open("wb") as handle:
        while chunk := file.file.read(1024 * 1024):
            handle.write(chunk)
    return rel(target)
