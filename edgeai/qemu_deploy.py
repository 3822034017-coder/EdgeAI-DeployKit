from pathlib import Path
import os
import shutil
import subprocess
from typing import Optional

from .generator import generate_demo
from .input_preparer import prepare_input_file
from .json_contract import normalize_contract
from .modelinfo import get_model_info


def _run(cmd, cwd=None):
    print(f"[RUN] {' '.join(str(x) for x in cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def _run_shell(cmd: str, cwd=None):
    print(f"[RUN] {cmd}")
    subprocess.run(cmd, cwd=cwd, shell=True, check=True, executable="/bin/bash")


def _infer_model_type(model_path: Path) -> str:
    text = f"{model_path.parent.name} {model_path.stem}".lower().replace("-", "").replace("_", "")
    if "mnist" in text or "lenet" in text:
        return "mnist"
    if "mobilenet" in text:
        return "mobilenetv2"
    if "resnet" in text:
        return "resnet18"
    if "yolo" in text:
        return "yolov5n"
    return model_path.parent.name.lower()


def _prepare_input_bin(model_path: Path, input_path: Path, output_dir: Path) -> Path:
    raw = get_model_info(model_path)
    raw["model_file"] = model_path.name
    raw["model_type"] = _infer_model_type(model_path)
    raw["input_dtype"] = "float32"
    raw["input_format"] = "NCHW"
    contract = normalize_contract(raw)

    tensor = prepare_input_file(input_path, contract).astype("float32", copy=False)
    input_bin = output_dir / "input.bin"
    input_bin.parent.mkdir(parents=True, exist_ok=True)
    tensor.tofile(input_bin)

    print(f"[INFO] Prepared QEMU input tensor: {input_bin}")
    print(f"[INFO] Source input: {input_path}")
    print(f"[INFO] Tensor shape: {list(tensor.shape)} dtype={tensor.dtype} bytes={tensor.nbytes}")
    return input_bin


def deploy_to_qemu(
    model_path: Path,
    input_path: Optional[Path] = None,
    kernel_path: Path = Path("/root/qemu-5.0.0/linux-5.10/arch/arm64/boot/Image"),
    initramfs_path: Path = Path("/root/initramfs.cpio"),
    output_dir: Path = Path("outputs/qemu_deploy"),
    memory: str = "1024M",
    onnxruntime_root: Path = Path("third_party/onnxruntime-aarch64"),
):
    """
    One-click QEMU deployment flow.

    Steps:
    1. Generate C++ demo from ONNX model.
    2. Cross-compile static ARM64 executable.
    3. Unpack initramfs.
    4. Inject executable and model into rootfs.
    5. Append auto-run command into /etc/init.d/rcS.
    6. Repack initramfs.
    7. Boot QEMU with the new initramfs.
    """

    project_root = Path(__file__).resolve().parents[1]
    onnxruntime_root = Path(onnxruntime_root).expanduser()
    if not onnxruntime_root.is_absolute():
        onnxruntime_root = (project_root / onnxruntime_root).resolve()
    else:
        onnxruntime_root = onnxruntime_root.resolve()
    ort_include = onnxruntime_root / "include"
    ort_lib = onnxruntime_root / "lib"
    ort_so = ort_lib / "libonnxruntime.so"

    if not ort_include.exists():
        raise FileNotFoundError(f"ONNX Runtime include not found: {ort_include}")

    if not ort_so.exists():
        raise FileNotFoundError(f"ONNX Runtime library not found: {ort_so}")
    model_path = Path(model_path).expanduser().resolve()
    kernel_path = Path(kernel_path).expanduser().resolve()
    initramfs_path = Path(initramfs_path).expanduser().resolve()
    output_dir = (project_root / output_dir).resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    if input_path is not None:
        input_path = Path(input_path).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

    if not kernel_path.exists():
        raise FileNotFoundError(f"Kernel Image not found: {kernel_path}")

    if not initramfs_path.exists():
        raise FileNotFoundError(f"initramfs not found: {initramfs_path}")

    toolchain_file = project_root / "cmake" / "aarch64-toolchain.cmake"
    if not toolchain_file.exists():
        raise FileNotFoundError(f"Toolchain file not found: {toolchain_file}")

    demo_dir = output_dir / "infer_demo"
    build_dir = demo_dir / "build-arm64-static"
    rootfs_dir = output_dir / "rootfs"
    new_initramfs = output_dir / "initramfs_edgeai.cpio"
    output_dir.mkdir(parents=True, exist_ok=True)
    input_bin = _prepare_input_bin(model_path, input_path, output_dir) if input_path else None

    print("========== EdgeAI QEMU One-click Deployment ==========")
    print(f"Model      : {model_path}")
    print(f"Input      : {input_path if input_path else 'random tensor'}")
    print(f"Kernel     : {kernel_path}")
    print(f"Initramfs  : {initramfs_path}")
    print(f"Output dir : {output_dir}")
    print("======================================================")

    # 1. Generate C++ demo
    print("\n[1/7] Generate C++ demo")
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
    demo_dir.mkdir(parents=True, exist_ok=True)
    generate_demo(model_path=model_path, output_dir=demo_dir)

    # 2. Cross-compile ARM64 static executable
    print("\n[2/7] Cross-compile ARM64 static executable")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    _run(
        [
            "cmake",
            "..",
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
            f"-DONNXRUNTIME_ROOT={onnxruntime_root}",
        ],
        cwd=build_dir,
    )
    _run(["make", "-j4"], cwd=build_dir)

    arm64_infer = build_dir / "arm64_infer"
    if not arm64_infer.exists():
        raise FileNotFoundError(f"ARM64 executable not generated: {arm64_infer}")

    _run(["file", str(arm64_infer)])

    # 3. Unpack initramfs
    print("\n[3/7] Unpack initramfs")
    if rootfs_dir.exists():
        shutil.rmtree(rootfs_dir)
    rootfs_dir.mkdir(parents=True, exist_ok=True)

    _run_shell(f"cpio -idmv < {initramfs_path}", cwd=rootfs_dir)

    # 4. Inject binary and model
    print("\n[4/7] Inject EdgeAI files into rootfs")
    edgeai_dir = rootfs_dir / "opt" / "edgeai"
    edgeai_dir.mkdir(parents=True, exist_ok=True)

    lib_dir = edgeai_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(arm64_infer, edgeai_dir / "arm64_infer")
    shutil.copy2(model_path, edgeai_dir / "model.onnx")
    if input_bin:
        shutil.copy2(input_bin, edgeai_dir / "input.bin")
    lib_dir = edgeai_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)

    for so_file in ort_lib.glob("libonnxruntime.so*"):
        target = lib_dir / so_file.name
        if so_file.is_symlink():
            real_file = so_file.resolve()
            shutil.copy2(real_file, target)
        elif so_file.is_file():
            shutil.copy2(so_file, target)

    os.chmod(edgeai_dir / "arm64_infer", 0o755)

    run_script = edgeai_dir / "run_edgeai.sh"
    run_script.write_text(
        """#!/bin/sh
echo ""
echo "====================================" > /dev/console
echo " EdgeAI QEMU ONNX Runtime Inference" > /dev/console
echo "====================================" > /dev/console
echo "[EdgeAI] Running real ONNX inference in QEMU..." > /dev/console

export LD_LIBRARY_PATH=/opt/edgeai/lib:$LD_LIBRARY_PATH

if [ -f /opt/edgeai/input.bin ]; then
    echo "[EdgeAI] Using input tensor: /opt/edgeai/input.bin" > /dev/console
    /opt/edgeai/arm64_infer /opt/edgeai/model.onnx /opt/edgeai/input.bin > /dev/console 2>&1
else
    echo "[EdgeAI] No input tensor found, using random input." > /dev/console
    /opt/edgeai/arm64_infer /opt/edgeai/model.onnx > /dev/console 2>&1
fi

echo "[EdgeAI] Inference finished." > /dev/console
echo "====================================" > /dev/console
""",
        encoding="utf-8",
    )
    os.chmod(run_script, 0o755)

    # 5. Modify rcS to auto-run demo
    print("\n[5/7] Configure auto-run in rootfs")
    rcs_path = rootfs_dir / "etc" / "init.d" / "rcS"

    if not rcs_path.exists():
        raise FileNotFoundError(
            f"{rcs_path} not found. This rootfs may not use /etc/init.d/rcS. "
            f"Please check its init system."
        )

    rcs_text = rcs_path.read_text(encoding="utf-8", errors="ignore")

    marker_start = "# ===== EdgeAI auto demo start ====="
    marker_end = "# ===== EdgeAI auto demo end ====="

    edgeai_boot_block = f"""
{marker_start}
if [ -x /opt/edgeai/run_edgeai.sh ]; then
    /opt/edgeai/run_edgeai.sh
fi
{marker_end}
"""

    if marker_start not in rcs_text:
        with rcs_path.open("a", encoding="utf-8") as f:
            f.write("\n")
            f.write(edgeai_boot_block)
    else:
        print("[INFO] EdgeAI auto-run block already exists in rcS.")

    os.chmod(rcs_path, 0o755)

    # 6. Repack initramfs
    print("\n[6/7] Repack initramfs")
    if new_initramfs.exists():
        new_initramfs.unlink()

    _run_shell(f"find . | cpio -o -H newc > {new_initramfs}", cwd=rootfs_dir)

    print(f"[INFO] New initramfs generated: {new_initramfs}")

    # 7. Boot QEMU
    print("\n[7/7] Boot QEMU")
    print("[INFO] QEMU will start now. To exit QEMU: press Ctrl+A, then X.")

    qemu_cmd = [
        "qemu-system-aarch64",
        "-M",
        "virt",
        "-cpu",
        "cortex-a53",
        "-m",
        memory,
        "-nographic",
        "-kernel",
        str(kernel_path),
        "-initrd",
        str(new_initramfs),
        "-append",
        "console=ttyAMA0 root=/dev/ram rdinit=/sbin/init",
    ]

    _run(qemu_cmd)
