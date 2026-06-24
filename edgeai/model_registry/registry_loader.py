from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_model_registry() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("registry.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = data.get("models", [])
    else:
        items = data
    return [item for item in items if isinstance(item, dict)]
