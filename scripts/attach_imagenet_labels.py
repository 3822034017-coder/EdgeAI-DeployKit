#!/usr/bin/env python3
"""
Attach ImageNet labels to an EdgeAI package.

Usage:
  python scripts/attach_imagenet_labels.py --package outputs/packages/mobilenet_local
  python scripts/attach_imagenet_labels.py --package outputs/packages/mobilenet_local --labels models/labels/imagenet_classes.txt
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def load_labels(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    labels: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # Support both "0: tench" and "tench" formats.
        if ":" in s:
            left, right = s.split(":", 1)
            if left.strip().isdigit():
                s = right.strip()
        # Support common CSV-like index,label.
        if "," in s:
            left, right = s.split(",", 1)
            if left.strip().isdigit():
                s = right.strip()
        labels.append(s)
    if not labels:
        raise SystemExit(f"No labels found in {path}")
    return labels


def main() -> int:
    ap = argparse.ArgumentParser(description="Attach ImageNet labels to EdgeAI package")
    ap.add_argument("--package", required=True, help="Package directory, e.g. outputs/packages/mobilenet_local")
    ap.add_argument("--labels", default="models/labels/imagenet_classes.txt", help="Label text file")
    args = ap.parse_args()

    package_dir = Path(args.package)
    labels_path = Path(args.labels)
    if not package_dir.exists():
        raise SystemExit(f"Package not found: {package_dir}")
    if not labels_path.exists():
        raise SystemExit(f"Label file not found: {labels_path}")

    labels = load_labels(labels_path)
    dst_txt = package_dir / "imagenet_classes.txt"
    shutil.copy2(labels_path, dst_txt)

    label_map = {str(i): label for i, label in enumerate(labels)}
    dst_json = package_dir / "label_map.json"
    dst_json.write_text(json.dumps(label_map, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "package_dir": str(package_dir),
        "labels": len(labels),
        "imagenet_classes": str(dst_txt),
        "label_map": str(dst_json),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
