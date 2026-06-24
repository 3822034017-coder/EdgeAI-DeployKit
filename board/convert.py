#!/usr/bin/env python3
"""Board-side batch ONNX to OM converter for Orange Pi AIPro."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from json_contract import load_json, normalize_json_file, save_json


DEFAULT_MODEL_DIR = Path("/home/HwHiAiUser/models/gongchuangmodel")


def prepare_atc_env() -> dict[str, str]:
    env = os.environ.copy()
    prefixes = [
        "/usr/local/python3.9.2/bin",
        "/usr/local/Ascend/ascend-toolkit/latest/bin",
    ]
    libs = [
        "/usr/local/python3.9.2/lib",
        "/usr/local/Ascend/ascend-toolkit/latest/lib64",
    ]
    env["PATH"] = ":".join(prefixes + [env.get("PATH", "")])
    env["LD_LIBRARY_PATH"] = ":".join(libs + [env.get("LD_LIBRARY_PATH", "")])
    env["PYTHONPATH"] = ":".join(
        [
            "/usr/local/Ascend/ascend-toolkit/latest/python/site-packages",
            env.get("PYTHONPATH", ""),
        ]
    )
    env.setdefault("ASCEND_OPP_PATH", "/usr/local/Ascend/ascend-toolkit/latest/opp")
    env.setdefault("ASCEND_AICPU_PATH", "/usr/local/Ascend/ascend-toolkit/latest")
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    return env


def find_atc() -> str:
    atc = shutil.which("atc")
    if atc:
        return atc
    for path in [
        "/usr/local/Ascend/ascend-toolkit/latest/bin/atc",
        "/usr/local/Ascend/ascend-toolkit/bin/atc",
    ]:
        if Path(path).exists():
            return path
    raise SystemExit(
        "[FAIL] atc not found. Run:\n"
        "  source /usr/local/Ascend/ascend-toolkit/set_env.sh"
    )


def resolve_profile(model_path: Path) -> Optional[Path]:
    candidates = [
        model_path.with_suffix(".json"),
        model_path.parent / "model.json",
        model_path.parent / "model_profile.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_profile(model_path: Path) -> tuple[dict, Optional[Path]]:
    profile_path = resolve_profile(model_path)
    if not profile_path:
        return {}, None
    return normalize_json_file(profile_path), profile_path


def build_atc_cmd(atc: str, model: Path, soc: str, extra_args: list[str]) -> tuple[list[str], dict, Optional[Path]]:
    profile, profile_path = load_profile(model)
    input_format = profile.get("input_format", "NCHW")
    input_shape = profile.get("input_shape_arg")

    cmd = [
        atc,
        "--framework=5",
        f"--model={model}",
        f"--output={model.with_suffix('')}",
        f"--soc_version={soc}",
        f"--input_format={input_format}",
    ]
    if input_shape:
        cmd.append(f"--input_shape={input_shape}")
    cmd.extend(extra_args)
    return cmd, profile, profile_path


def update_profile(profile_path: Optional[Path], profile: dict, result: dict) -> None:
    if not profile_path:
        return
    raw = load_json(profile_path)
    raw["deployment_contract"] = {key: value for key, value in profile.items() if key != "raw"}
    raw.setdefault("board", {})
    raw["board"]["om_convert"] = result["status"]
    raw["board"]["om_path"] = result.get("om_path")
    raw["board"]["om_error"] = result.get("error")
    raw["board"]["atc_command"] = result.get("atc_command")
    raw["input_name"] = profile.get("input_name")
    raw["input_shape"] = profile.get("input_shape")
    raw["input_format"] = profile.get("input_format")
    raw["input_shape_arg"] = profile.get("input_shape_arg")
    save_json(raw, profile_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert ONNX models to OM with ATC.")
    parser.add_argument("--dir", default=str(DEFAULT_MODEL_DIR), help="directory containing ONNX files")
    parser.add_argument("--soc-version", default="Ascend310B4")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--extra-args", nargs=argparse.REMAINDER, default=[])
    args = parser.parse_args()

    model_dir = Path(args.dir).expanduser().resolve()
    if not model_dir.exists():
        print(f"[FAIL] model dir not found: {model_dir}")
        return 2

    env = prepare_atc_env()
    atc = find_atc()
    models = sorted(model_dir.glob("*.onnx"))
    if not models:
        print(f"[FAIL] no .onnx files found in {model_dir}")
        return 2

    print(f"[INFO] ATC: {atc}")
    print(f"[INFO] Model dir: {model_dir}")
    results = []
    ok = 0
    failed = 0
    skipped = 0

    for model in models:
        om_path = model.with_suffix(".om")
        if om_path.exists() and not args.force:
            print(f"[SKIP] {om_path.name} exists")
            skipped += 1
            results.append(
                {
                    "model": model.name,
                    "status": "SKIPPED",
                    "om_path": str(om_path),
                    "error": None,
                }
            )
            continue

        cmd, profile, profile_path = build_atc_cmd(atc, model, args.soc_version, args.extra_args)
        print("[CMD] " + " ".join(str(x) for x in cmd))
        if args.dry_run:
            ok += 1
            result = {
                "model": model.name,
                "status": "DRY_RUN",
                "om_path": str(om_path),
                "error": None,
                "atc_command": " ".join(str(x) for x in cmd),
            }
            update_profile(profile_path, profile, result)
            results.append(result)
            continue

        completed = subprocess.run(cmd, capture_output=True, text=True, env=env)
        success = completed.returncode == 0 and om_path.exists()
        result = {
            "model": model.name,
            "status": "SUCCESS" if success else "FAILED",
            "om_path": str(om_path) if success else None,
            "error": None if success else (completed.stderr or completed.stdout),
            "atc_command": " ".join(str(x) for x in cmd),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        update_profile(profile_path, profile, result)
        results.append(result)

        if success:
            print(f"[OK] {model.name} -> {om_path.name}")
            ok += 1
        else:
            print(f"[FAIL] {model.name}, exit={completed.returncode}")
            failed += 1

    save_json(
        {
            "status": "FAILED" if failed else "SUCCESS",
            "converted": ok,
            "skipped": skipped,
            "failed": failed,
            "results": results,
        },
        model_dir / "convert_result.json",
    )
    print(f"[SUMMARY] converted={ok}, skipped={skipped}, failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
