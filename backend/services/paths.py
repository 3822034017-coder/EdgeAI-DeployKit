from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("EDGEAI_PROJECT_ROOT", Path(__file__).resolve().parents[2])).resolve()
OUTPUTS_DIR = Path(os.environ.get("EDGEAI_OUTPUTS", PROJECT_ROOT / "outputs")).resolve()
REPORTS_DIR = Path(os.environ.get("EDGEAI_REPORTS", PROJECT_ROOT / "reports")).resolve()
INPUTS_DIR = Path(os.environ.get("EDGEAI_INPUTS", PROJECT_ROOT / "inputs")).resolve()
JOBS_DIR = OUTPUTS_DIR / "jobs"
MATRIX_JSON = OUTPUTS_DIR / "model_matrix" / "matrix.json"


def ensure_runtime_dirs() -> None:
    for path in [OUTPUTS_DIR, REPORTS_DIR, INPUTS_DIR, JOBS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def rel(path: str | Path) -> str:
    p = Path(path).resolve()
    try:
        return str(p.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(p)
