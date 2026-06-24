"""Run a synced package on Orange Pi AIPro and collect board results."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Optional

from .json_contract import load_json, save_json


REMOTE_ROOT = "~/edgeai_models"


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print()
    print("[CMD]", " ".join(shlex.quote(str(x)) for x in cmd))
    print()
    return subprocess.run(cmd, check=check)


def _target(host: str, user: Optional[str]) -> str:
    if "@" in host or not user:
        return host
    return f"{user}@{host}"


def _remote_dir(model_name: str, remote_root: str = REMOTE_ROOT) -> str:
    return f"{remote_root.rstrip('/')}/{model_name}"


def _bash_path(path: str) -> str:
    if path.startswith("~/"):
        return "$HOME/" + shlex.quote(path[2:])
    return shlex.quote(path)


def _resolve_package_dir(package_dir: Optional[Path], model_name: Optional[str]) -> Path:
    if package_dir:
        return Path(package_dir).expanduser().resolve()
    if not model_name:
        raise ValueError("package_dir or model_name is required")
    return (Path("outputs/packages") / model_name).resolve()


def _read_model_name(package_dir: Path, model_name: Optional[str]) -> str:
    if model_name:
        return model_name
    model_json = package_dir / "model.json"
    if model_json.exists():
        data = load_json(model_json)
        return str(data.get("model_type") or data.get("model_name") or package_dir.name)
    return package_dir.name


def _ssh_script(target: str, script: str) -> subprocess.CompletedProcess:
    remote_command = f"bash -lc {shlex.quote(script)}"
    return _run(["ssh", target, remote_command], check=False)


def _scp_from(target: str, remote: str, local: Path) -> None:
    local.parent.mkdir(parents=True, exist_ok=True)
    _run(["scp", f"{target}:{remote}", str(local)])


def board_run(
    host: str,
    model_name: Optional[str] = None,
    port: int = 7891,
    output_dir: Optional[Path] = None,
    package_dir: Optional[Path] = None,
    user: str = "HwHiAiUser",
    remote_root: str = REMOTE_ROOT,
    remote_dir: Optional[str] = None,
    wait: float = 3.0,
    force_convert: bool = False,
) -> Path:
    """Convert/run a previously synced package on the board.

    The remote directory must contain model.onnx, model.json, input.npy,
    convert.py, run_model.py, and json_contract.py.
    """
    package_path = _resolve_package_dir(package_dir, model_name)
    resolved_model_name = _read_model_name(package_path, model_name)
    target = _target(host, user)
    final_remote_dir = remote_dir or _remote_dir(resolved_model_name, remote_root)
    local_output = Path(output_dir or package_path).expanduser().resolve()
    local_output.mkdir(parents=True, exist_ok=True)

    force_arg = "--force" if force_convert else ""
    script = f"""
set -e
cd {_bash_path(final_remote_dir)}
if [ -f /usr/local/Ascend/ascend-toolkit/set_env.sh ]; then
  source /usr/local/Ascend/ascend-toolkit/set_env.sh
elif [ -f /usr/local/Ascend/ascend-toolkit/latest/set_env.sh ]; then
  source /usr/local/Ascend/ascend-toolkit/latest/set_env.sh
fi
export PATH=/usr/local/python3.9.2/bin:/usr/local/Ascend/ascend-toolkit/latest/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/python3.9.2/lib:/usr/local/Ascend/ascend-toolkit/latest/lib64:$LD_LIBRARY_PATH
export PYTHONPATH=/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:$PYTHONPATH
export ASCEND_OPP_PATH=/usr/local/Ascend/ascend-toolkit/latest/opp
export ASCEND_AICPU_PATH=/usr/local/Ascend/ascend-toolkit/latest
export LC_ALL=C
export LANG=C
python3 convert.py --dir . {force_arg} > convert.log 2>&1
port_pids=$(ss -tlnp | grep ":{port}" | sed -n 's/.*pid=\\([0-9][0-9]*\\).*/\\1/p' | sort -u || true)
if [ -n "$port_pids" ]; then
  kill $port_pids || true
  sleep 3
fi
nohup /usr/local/bin/airloader -m "$(pwd)/model.om" -p {port} > airloader.log 2>&1 &
sleep {wait}
if ! ss -tlnp | grep -q ":{port}"; then
  cat airloader.log
  exit 1
fi
python3 run_model.py --json model.json --input input.npy -r 127.0.0.1 -p {port} -o board_result.json --update-json > run.log 2>&1
run_rc=$?
if [ $run_rc -ne 0 ]; then
  cat run.log
  exit $run_rc
fi
"""
    completed = _ssh_script(target, script)
    remote_success = completed.returncode == 0

    pulled = []
    pull_files = [
        "board_result.json",
        "model.json",
        "convert_result.json",
        "convert.log",
        "airloader.log",
        "run.log",
        "yolo_result.jpg",
        f"{resolved_model_name}_info.jpg",
    ]
    for name in pull_files:
        try:
            _scp_from(target, f"{final_remote_dir}/{name}", local_output / name)
            pulled.append(name)
        except subprocess.CalledProcessError:
            print(f"[WARN] could not pull {name}")

    # Fixup board_result.json: replace board-side annotated_image path with local copy
    local_board = local_output / "board_result.json"
    if local_board.exists():
        board_data = load_json(local_board)
        remote_img = board_data.get("annotated_image")
        if remote_img:
            local_img = None
            for candidate in ["yolo_result.jpg", f"{resolved_model_name}_info.jpg"]:
                c = local_output / candidate
                if c.exists():
                    local_img = str(c)
                    break
            if local_img and local_img != remote_img:
                board_data["annotated_image"] = local_img
                save_json(board_data, local_board)
                print(f"[OK] fixed annotated_image -> {local_img}")

    result_file = local_output / "board_run_result.json"
    result = {
        "status": "success" if remote_success else "failed",
        "host": target,
        "remote_dir": final_remote_dir,
        "model_name": resolved_model_name,
        "port": port,
        "remote_returncode": completed.returncode,
        "pulled": pulled,
        "board_result": str(local_output / "board_result.json"),
    }
    save_json(result, result_file)
    if not remote_success:
        raise RuntimeError(f"board run failed, logs pulled to {local_output}")

    print(f"[OK] board result pulled to {local_output}")
    return result_file
