#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from edgeai.task_system import create_or_update_model_task, read_model_task

def main() -> int:
    ap = argparse.ArgumentParser(description="Create or inspect model_task.json for an EdgeAI package.")
    ap.add_argument("--package", required=True)
    ap.add_argument("--task-type", default="auto")
    ap.add_argument("--label-map", default=None)
    ap.add_argument("--label-language", default="zh")
    ap.add_argument("--info", action="store_true")
    args = ap.parse_args()
    result = read_model_task(args.package, False) if args.info else create_or_update_model_task(args.package, args.task_type, args.label_map, args.label_language)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1
if __name__ == "__main__": raise SystemExit(main())
