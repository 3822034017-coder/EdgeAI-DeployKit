from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgeai.tf_universal_importer import probe_tensorflow_model  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe TensorFlow/Keras/SavedModel/TFLite model containers.")
    parser.add_argument("--source-model", required=True)
    parser.add_argument("--input-shape", default=None)
    args = parser.parse_args()
    try:
        result = probe_tensorflow_model(args.source_model, input_shape=args.input_shape)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0 if result.get("ok") else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
