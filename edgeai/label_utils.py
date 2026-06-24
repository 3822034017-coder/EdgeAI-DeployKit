"""Classification label helpers used when generating result JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


IMAGENET_MODEL_TYPES = {"mobilenetv2", "resnet18"}

# Fallback for common demo classes. Put the full 1000-class list in
# edgeai/labels/imagenet_classes.txt for complete ImageNet translation.
IMAGENET_FALLBACK_LABELS = {
    281: "tabby cat",
    282: "tiger cat",
    283: "Persian cat",
    284: "Siamese cat",
    285: "Egyptian cat",
}


def default_imagenet_label_path() -> Path:
    return Path(__file__).resolve().parent / "labels" / "imagenet_classes.txt"


def load_imagenet_labels(path: Optional[Path] = None) -> list[str]:
    label_path = Path(path or default_imagenet_label_path())
    if not label_path.exists():
        return []
    return [
        line.strip()
        for line in label_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def _as_index(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def imagenet_label(index: Any, labels: Optional[list[str]] = None) -> Optional[str]:
    idx = _as_index(index)
    if idx is None:
        return None

    resolved_labels = labels if labels is not None else load_imagenet_labels()
    if 0 <= idx < len(resolved_labels):
        return resolved_labels[idx]
    return IMAGENET_FALLBACK_LABELS.get(idx)


def should_translate(model_type: Any) -> bool:
    return str(model_type or "").lower() in IMAGENET_MODEL_TYPES


def enrich_classification_labels(
    payload: dict[str, Any],
    model_type: Any,
    labels: Optional[list[str]] = None,
) -> bool:
    """Add human-readable ImageNet labels while keeping numeric indices."""
    if not should_translate(model_type):
        return False

    changed = False
    top1 = payload.get("top1")
    if top1 is None:
        top1 = payload.get("predict")

    label = imagenet_label(top1, labels)
    if label:
        payload["top1_label"] = label
        payload["predict_label"] = label
        changed = True

    top5 = payload.get("top5")
    if isinstance(top5, list):
        for item in top5:
            if not isinstance(item, dict):
                continue
            item_label = imagenet_label(item.get("index"), labels)
            if item_label:
                item["label"] = item_label
                changed = True

    return changed
