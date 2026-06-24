from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.schemas import ArtifactItem
from backend.services.paths import MATRIX_JSON, OUTPUTS_DIR, REPORTS_DIR, rel


def read_json(path: Path) -> Any:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []


def read_matrix() -> list[dict[str, Any]]:
    data = read_json(MATRIX_JSON)
    return data if isinstance(data, list) else []


def artifact_kind(path: Path) -> str:
    rp = rel(path)
    if rp.startswith("reports/"):
        return "report"
    if "packages" in path.parts:
        return "package"
    if "benchmark" in path.parts or "benchmark" in path.name:
        return "benchmark"
    if path.name == "matrix.json":
        return "matrix"
    return "other"


def list_artifacts() -> list[ArtifactItem]:
    candidates: list[Path] = []
    for base in [REPORTS_DIR, OUTPUTS_DIR / "model_matrix", OUTPUTS_DIR / "packages", OUTPUTS_DIR / "benchmark"]:
        if base.exists():
            candidates.extend([p for p in base.rglob("*") if p.is_file()])
    items: list[ArtifactItem] = []
    for path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[:120]:
        stat = path.stat()
        items.append(ArtifactItem(
            name=path.name,
            path=rel(path),
            kind=artifact_kind(path),
            size_mb=round(stat.st_size / 1024 / 1024, 4),
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        ))
    return items
