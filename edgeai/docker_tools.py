from pathlib import Path
import subprocess

from .resources import resource_path


def _run(cmd):
    print("[RUN]", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def docker_build(
    tag: str = "edgeai-deploykit:deploy",
    dockerfile: Path = Path("docker/Dockerfile.deploy"),
):
    project_root = Path.cwd()
    if dockerfile.is_absolute():
        dockerfile_path = dockerfile
        build_context = dockerfile.parent.parent
    else:
        checkout_dockerfile = project_root / dockerfile
        if checkout_dockerfile.exists():
            dockerfile_path = checkout_dockerfile
            build_context = project_root
        else:
            dockerfile_path = resource_path(*dockerfile.parts)
            build_context = dockerfile_path.parents[1]

    if not dockerfile_path.exists():
        raise FileNotFoundError(f"Dockerfile not found: {dockerfile_path}")

    _run([
        "docker",
        "build",
        "-f",
        str(dockerfile_path),
        "-t",
        tag,
        str(build_context),
    ])


def docker_run_qemu(
    model: Path,
    tag: str = "edgeai-deploykit:deploy",
    qemu_dir: Path = Path("/root/qemu-5.0.0"),
    initramfs: Path = Path("/root/initramfs.cpio"),
    toolchain_dir: Path = Path("/root/tools/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu"),
    memory: str = "1024M",
    onnxruntime_root: Path = Path("third_party/onnxruntime-aarch64"),
):
    project_root = Path.cwd().resolve()
    model_path = project_root / model

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    if not qemu_dir.exists():
        raise FileNotFoundError(f"QEMU directory not found: {qemu_dir}")

    if not initramfs.exists():
        raise FileNotFoundError(f"initramfs not found: {initramfs}")

    compiler = toolchain_dir / "bin" / "aarch64-linux-gnu-g++"
    if not compiler.exists():
        raise FileNotFoundError(
            f"ARM64 compiler not found: {compiler}\n"
            f"Please pass the correct toolchain directory with --toolchain-dir."
        )

    inner_cmd = (
        "cd /workspace && "
        "pip3 install -e . --no-build-isolation -i https://pypi.tuna.tsinghua.edu.cn/simple && "
        "edgeai deploy-qemu "
        f"--model {model} "
        "--kernel /qemu-5.0.0/linux-5.10/arch/arm64/boot/Image "
        "--initramfs /base-initramfs.cpio "
        "--output outputs/qemu_deploy "
        f"--memory {memory} "
        f"--onnxruntime-root {onnxruntime_root}"
    )

    _run([
        "docker",
        "run",
        "--rm",
        "-it",
        "-v",
        f"{project_root}:/workspace",
        "-v",
        f"{qemu_dir}:/qemu-5.0.0:ro",
        "-v",
        f"{initramfs}:/base-initramfs.cpio:ro",
        "-v",
        f"{toolchain_dir}:/opt/aarch64-toolchain:ro",
        "-e",
        "AARCH64_TOOLCHAIN_ROOT=/opt/aarch64-toolchain",
        "-e",
        "PATH=/opt/aarch64-toolchain/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        tag,
        "bash",
        "-lc",
        inner_cmd,
    ])
