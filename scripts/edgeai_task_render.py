#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgeai.task_result import render_task_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Render task-aware inference result into task_result.json")
    parser.add_argument("--package", required=True, help="Package directory or package name")
    parser.add_argument("--force", action="store_true", help="Regenerate even if task_result.json exists")
    args = parser.parse_args()
    result = render_task_result(args.package, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
