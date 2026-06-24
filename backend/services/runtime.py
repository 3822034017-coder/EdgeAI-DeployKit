from __future__ import annotations

import shutil
import sys
from pathlib import Path

from backend.schemas import HealthItem, HealthResponse
from backend.services.paths import OUTPUTS_DIR, PROJECT_ROOT, REPORTS_DIR


def tool_check(name: str, command: str) -> HealthItem:
    found = shutil.which(command)
    return HealthItem(name=name, command=command, available=found is not None, detail=found)


def runtime_health() -> HealthResponse:
    checks = [
        HealthItem(name="Python runtime", command=sys.executable, available=Path(sys.executable).exists(), detail=sys.version.split()[0]),
        HealthItem(name="edgeai module", command=f"{sys.executable} -m edgeai.cli", available=(PROJECT_ROOT / "edgeai" / "cli.py").exists(), detail=str(PROJECT_ROOT / "edgeai" / "cli.py")),
        tool_check("edgeai console script", "edgeai"),
        tool_check("Python launcher", "python"),
        tool_check("Python 3 launcher", "python3"),
        tool_check("cmake", "cmake"),
        tool_check("make", "make"),
        tool_check("gcc", "gcc"),
        tool_check("g++", "g++"),
        tool_check("qemu-system-aarch64", "qemu-system-aarch64"),
        tool_check("atc", "atc"),
        tool_check("docker", "docker"),
    ]
    sdk = Path("/opt/openeuler-aarch64/environment-setup-aarch64-openeuler-linux")
    checks.append(HealthItem(name="openEuler aarch64 SDK", command=None, available=sdk.exists(), detail=str(sdk)))
    return HealthResponse(project_root=str(PROJECT_ROOT), outputs_dir=str(OUTPUTS_DIR), reports_dir=str(REPORTS_DIR), checks=checks)
