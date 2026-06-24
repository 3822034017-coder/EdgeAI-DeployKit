#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MODULES = [
    "typer",
    "pydantic",
    "fastapi",
    "uvicorn",
    "onnx",
    "onnxruntime",
    "numpy",
    "PIL",
]

OPTIONAL_MODULES = [
    "weasyprint",
    "tf2onnx",
    "tensorflow",
    "h5py",
    "torch",
    "torchvision",
    "skl2onnx",
    "onnxmltools",
]

TOOLS = [
    "python3",
    "node",
    "corepack",
    "pnpm",
    "cmake",
    "gcc",
    "g++",
]


def module_available(name: str) -> dict[str, Any]:
    found = importlib.util.find_spec(name) is not None
    version = None
    if found:
        try:
            mod = __import__(name)
            version = getattr(mod, "__version__", None)
        except Exception:
            version = None
    return {"name": name, "available": found, "version": version}


def tool_available(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    version = None
    if path:
        try:
            proc = subprocess.run(
                [path, "--version"],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=5,
                check=False,
            )
            version = (proc.stdout or "").splitlines()[0][:160] if proc.stdout else None
        except Exception as exc:
            version = f"version check failed: {type(exc).__name__}: {exc}"
    return {"name": name, "available": path is not None, "path": path, "version": version}


def edgeai_cli_check() -> dict[str, Any]:
    cmd = [sys.executable, "-m", "edgeai.cli", "--help"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
        )
        return {
            "command": " ".join(cmd),
            "available": proc.returncode == 0,
            "code": proc.returncode,
            "output_tail": (proc.stdout or "")[-1200:],
        }
    except Exception as exc:
        return {
            "command": " ".join(cmd),
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Linux runtime readiness for EdgeAI-DeployKit.")
    parser.add_argument("--json", dest="json_path", default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    required = [module_available(name) for name in REQUIRED_MODULES]
    optional = [module_available(name) for name in OPTIONAL_MODULES]
    tools = [tool_available(name) for name in TOOLS]
    required_missing = [item["name"] for item in required if not item["available"]]

    result = {
        "ok": not required_missing,
        "project_root": str(ROOT),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "executable": sys.executable,
        },
        "required_modules": required,
        "optional_modules": optional,
        "tools": tools,
        "edgeai_cli": edgeai_cli_check(),
        "required_missing": required_missing,
        "notes": [
            "TensorFlow/Keras conversion requires optional modules: tensorflow, tf2onnx, h5py.",
            "PyTorch conversion requires optional modules: torch, torchvision.",
            "Frontend startup requires Node.js 20+ and pnpm/Corepack.",
        ],
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.json_path:
        path = Path(args.json_path)
        if not path.is_absolute():
            path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
