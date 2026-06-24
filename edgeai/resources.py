"""Runtime resource lookup helpers.

The project can run from a source checkout or from an installed package.  Some
CLI commands need non-Python resources such as templates, CMake files and
Dockerfiles, so this module resolves those files in both layouts.
"""

from __future__ import annotations

import sys
from pathlib import Path


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str | Path) -> Path:
    relative = Path(*parts)
    candidates = [
        Path.cwd() / relative,
        source_root() / relative,
        Path(sys.prefix) / "edgeai_deploykit" / relative,
        Path(sys.base_prefix) / "edgeai_deploykit" / relative,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    searched = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise FileNotFoundError(f"Resource not found: {relative}\nSearched:\n{searched}")
