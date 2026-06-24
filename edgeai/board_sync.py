"""Sync deploy package to Orange Pi AIPro.

Board layout:
  ~/edgeai_models/<model_name>/
    model.onnx
    model.json
    input.npy
    run_model.py
    convert.py
    json_contract.py
"""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Optional

from .json_contract import normalize_json_file


REMOTE_ROOT = "~/edgeai_models"


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print()
    print("[CMD]", " ".join(shlex.quote(str(x)) for x in cmd))
    print()
    return subprocess.run(cmd, check=check)


def _ssh(target: str, command: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run(["ssh", target, command], check=check)


def _scp(src: Path, target: str, dest: str) -> None:
    _run(["scp", str(src), f"{target}:{dest}"])


def _target(host: str, user: Optional[str]) -> str:
    if "@" in host or not user:
        return host
    return f"{user}@{host}"


def _remote_dir(model_name: str, remote_root: str = REMOTE_ROOT) -> str:
    return f"{remote_root.rstrip('/')}/{model_name}"


def _check_space(target: str, min_free_gb: float) -> None:
    command = (
        "python3 - <<'PY'\n"
        "import shutil\n"
        "print(shutil.disk_usage('/home').free / 1024 / 1024 / 1024)\n"
        "PY"
    )
    out = subprocess.check_output(["ssh", target, command], text=True).strip()
    free_gb = float(out.splitlines()[-1])
    print(f"[INFO] /home free space: {free_gb:.2f} GB")
    if free_gb < min_free_gb:
        raise RuntimeError(f"OrangePi /home free space < {min_free_gb} GB")


def _resolve_package_dir(package_dir: Optional[Path], model_name: Optional[str]) -> Path:
    if package_dir:
        return Path(package_dir).expanduser().resolve()
    if not model_name:
        raise ValueError("package_dir or model_name is required")
    return (Path("outputs/packages") / model_name).resolve()


def board_sync(
    package_dir: Optional[Path] = None,
    host: Optional[str] = None,
    model_name: Optional[str] = None,
    user: str = "HwHiAiUser",
    remote_root: str = REMOTE_ROOT,
    remote_dir: Optional[str] = None,
    min_free_gb: float = 2.0,
) -> str:
    """Upload a generated package to Orange Pi.

    Args:
        package_dir: package directory containing model.onnx/model.json/input.npy.
        host: board host. Can be "192.168.0.36" or "HwHiAiUser@192.168.0.36".
        model_name: optional remote model directory name. Defaults to JSON model_type.
        user: SSH user used when host does not contain "@".
        remote_root: remote root, default ~/edgeai_models.
        remote_dir: explicit remote directory override.
        min_free_gb: fail when /home free space is below this value.
    """
    if not host:
        raise ValueError("host is required")

    package_path = _resolve_package_dir(package_dir, model_name)
    if not package_path.exists():
        raise FileNotFoundError(f"package not found: {package_path}")

    required = ["model.onnx", "model.json", "input.npy"]
    for name in required:
        if not (package_path / name).exists():
            raise FileNotFoundError(f"package missing {name}: {package_path}")

    upload_files = list(required)
    package_result_path = package_path / "package_result.json"
    if package_result_path.exists():
        package_result = json.loads(package_result_path.read_text(encoding="utf-8-sig"))
        for name in package_result.get("files", []):
            if name not in upload_files and (package_path / name).exists():
                upload_files.append(name)
    for path in sorted(package_path.glob("source_image.*")):
        if path.name not in upload_files:
            upload_files.append(path.name)

    contract = normalize_json_file(package_path / "model.json")
    model_name = model_name or contract["model_type"]
    target = _target(host, user)
    final_remote_dir = remote_dir or _remote_dir(model_name, remote_root)

    _check_space(target, min_free_gb=min_free_gb)
    _ssh(target, f"mkdir -p {final_remote_dir}")

    for name in upload_files:
        _scp(package_path / name, target, f"{final_remote_dir}/{name}")

    board_root = Path(__file__).resolve().parents[1] / "board"
    for name in ["run_model.py", "convert.py", "json_contract.py"]:
        src = board_root / name
        if not src.exists():
            raise FileNotFoundError(f"board script not found: {src}")
        _scp(src, target, f"{final_remote_dir}/{name}")

    sync_result = {
        "status": "success",
        "host": target,
        "remote_dir": final_remote_dir,
        "model_name": model_name,
        "uploaded": upload_files + ["run_model.py", "convert.py", "json_contract.py"],
    }
    (package_path / "board_sync_result.json").write_text(
        json.dumps(sync_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"[OK] synced package to {target}:{final_remote_dir}")
    print()
    return final_remote_dir
