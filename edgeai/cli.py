from pathlib import Path
import shlex
from typing import Optional

import typer
import json

from .om_converter import convert_onnx_to_om
from .benchmark import benchmark_model
from .checker import check_model
from .generator import generate_demo
from .quantizer import quantize_model
from .report import compare_reports, generate_html_report, generate_markdown_report
from .report import generate_matrix_markdown, generate_matrix_html, markdown_to_pdf
from .qemu_deploy import deploy_to_qemu
from .docker_tools import docker_build, docker_run_qemu
from .model_matrix import generate_matrix
from .deploy_packager import generate_package, package_model
from .modelinfo import get_model_info
from .board_sync import board_sync
from .board_runner import board_run
from .input_preparer import create_input_npy
from .matrix_report import generate_matrix_reports
from .pc_aipro_report import generate_pc_aipro_reports

from .local_cli_ext import register_local_run_commands

app = typer.Typer(help="EdgeAI-DeployKit command line tool")


# EDGEAI_MODEL_PROBE_COMMAND
@app.command("model-probe")
def model_probe_cmd(
    source_model: str = typer.Option(..., "--source-model", help="Path to model file or directory"),
    framework: str = typer.Option("auto", "--framework", help="Framework hint: auto/onnx/pytorch/tensorflow/sklearn"),
):
    """Probe a model and suggest conversion parameters from the EdgeAI model intelligence registry."""
    import json
    from .model_intelligence import probe_model

    print(json.dumps(probe_model(source_model, framework), ensure_ascii=False, indent=2))


# EDGEAI_TASK_RENDER_COMMAND_HOTFIX
@app.command("task-render")
def task_render_cmd(
    package: str = typer.Option(..., "--package", help="Path to model package directory or package name"),
    force: bool = typer.Option(False, "--force/--no-force", help="Regenerate task_result.json even if it exists"),
):
    """Render task-aware inference result into task_result.json."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "edgeai_task_render.py"
    cmd = [sys.executable, str(script), "--package", package]
    if force:
        cmd.append("--force")
    raise typer.Exit(subprocess.call(cmd))


# Local ONNX user-model foundation commands
# Adds: init-package, analyze, prepare-input, local-run
register_local_run_commands(app)


@app.command()
def check(model: Path = typer.Option(..., "--model", "-m")):
    check_model(model)


@app.command()
def quantize(
    model: Path = typer.Option(..., "--model", "-m"),
    output: Path = typer.Option(..., "--output", "-o"),
):
    quantize_model(model, output)


@app.command()
def benchmark(
    model: Path = typer.Option(..., "--model", "-m"),
    repeat: int = typer.Option(50, "--repeat", "-r"),
    output: Path = typer.Option(Path("outputs/benchmark.json"), "--output", "-o"),
    input_image: Optional[Path] = typer.Option(None, "--input", "-i",
        help="Optional real image for inference (classification/detection results included)"),
    model_type: Optional[str] = typer.Option(None, "--type", "-t",
        help="Model type: mnist / mobilenetv2 / resnet18 / yolov5n"),
):
    benchmark_model(model, repeat, output, input_image, model_type)


@app.command()
def report(
    input_path: Optional[Path] = typer.Option(None, "--input", "-i"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    package_dir: Optional[Path] = typer.Option(
        None,
        "--package",
        "-p",
        help="New local-run package directory, e.g. outputs/packages/mobilenet_local",
    ),
    mirror_to_reports: bool = typer.Option(
        True,
        "--mirror-to-reports/--no-mirror-to-reports",
        help="Also write reports/<model_name>_local_report.md",
    ),
):
    """Generate reports.

    New flow:
      edgeai report --package outputs/packages/<model_name>

    Legacy flow:
      edgeai report --input benchmark.json --output report.md
      edgeai report
    """
    if package_dir is not None:
        from .local_report import generate_local_package_report

        result = generate_local_package_report(
            package_dir=package_dir,
            output=output,
            mirror_to_reports=mirror_to_reports,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if input_path and output:
        generate_markdown_report(input_path, output)
    else:
        generate_matrix_markdown()

@app.command()
def compare(
    fp32: Path = typer.Option(None, "--fp32"),
    int8: Path = typer.Option(None, "--int8"),
    output: Path = typer.Option(None, "--output", "-o"),
):
    """PC vs Board latency comparison from matrix.json.

    If --fp32 and --int8 and --output are given, generate an FP32-vs-INT8
    comparison report from two benchmark JSONs.  Otherwise, print a
    PC vs Board comparison from the full matrix (run 'edgeai matrix' first).
    """
    if fp32 and int8 and output:
        compare_reports(fp32, int8, output)
    else:
        compare_reports()


@app.command()
def html(
    input_path: Path = typer.Option(None, "--input", "-i"),
    output: Path = typer.Option(None, "--output", "-o"),
    model: Optional[str] = typer.Option(None, "--model", help="Only generate HTML for current model/package name"),
):
    """Generate HTML report."""
    if input_path and output:
        generate_html_report(input_path, output)
    else:
        generate_matrix_html(model=model)


@app.command()
def pdf(
    md_path: Optional[Path] = typer.Option(None, "--input", "-i",
        help="Markdown file (default: reports/edgeai_report.md)"),
    pdf_path: Optional[Path] = typer.Option(None, "--output", "-o",
        help="PDF output (default: reports/edgeai_report.pdf)"),
):
    """Convert Markdown report to PDF (requires pandoc or weasyprint)."""
    markdown_to_pdf(md_path, pdf_path)


@app.command()
def generate(
    model: Path = typer.Option(..., "--model", "-m"),
    output: Path = typer.Option(Path("outputs/infer_demo"), "--output", "-o"),
):
    generate_demo(model, output)



@app.command("deploy-qemu")
def deploy_qemu(
    model: Path = typer.Option(..., "--model", "-m", help="Input ONNX model path"),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="Optional image/.npy/.bin/.txt/.csv converted to QEMU input.bin",
    ),
    kernel: Path = typer.Option(
        Path("/root/qemu-5.0.0/linux-5.10/arch/arm64/boot/Image"),
        "--kernel",
        help="ARM64 Linux kernel Image path",
    ),
    initramfs: Path = typer.Option(
        Path("/root/initramfs.cpio"),
        "--initramfs",
        help="Base initramfs.cpio path",
    ),
    output: Path = typer.Option(
        Path("outputs/qemu_deploy"),
        "--output",
        "-o",
        help="Output directory for generated QEMU deployment files",
    ),
    memory: str = typer.Option("1024M", "--memory", help="QEMU memory size"),
    onnxruntime_root: Path = typer.Option(
    Path("third_party/onnxruntime-aarch64"),
    "--onnxruntime-root",
    help="ONNX Runtime ARM64 root directory",
    ),
):
    deploy_to_qemu(
        model_path=model,
        input_path=input_file,
        kernel_path=kernel,
        initramfs_path=initramfs,
        output_dir=output,
        memory=memory,
        onnxruntime_root=onnxruntime_root,
    )   



@app.command("docker-build")
def docker_build_cmd(
    tag: str = typer.Option("edgeai-deploykit:deploy", "--tag"),
):
    docker_build(tag=tag)


@app.command("docker-run-qemu")
def docker_run_qemu_cmd(
    model: Path = typer.Option(..., "--model", "-m"),
    tag: str = typer.Option("edgeai-deploykit:deploy", "--tag"),
    qemu_dir: Path = typer.Option(Path("/root/qemu-5.0.0"), "--qemu-dir"),
    initramfs: Path = typer.Option(Path("/root/initramfs.cpio"), "--initramfs"),
    toolchain_dir: Path = typer.Option(
        Path("/root/tools/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu"),
        "--toolchain-dir",
    ),
    memory: str = typer.Option("1024M", "--memory"),
    onnxruntime_root: Path = typer.Option(
    Path("third_party/onnxruntime-aarch64"),
    "--onnxruntime-root",
    help="ONNX Runtime ARM64 root directory",
    ),
):
    docker_run_qemu(
        model=model,
        tag=tag,
        qemu_dir=qemu_dir,
        initramfs=initramfs,
        toolchain_dir=toolchain_dir,
        memory=memory,
        onnxruntime_root=onnxruntime_root,
    )    

@app.command()
def matrix():

    generate_matrix()

@app.command()
def package(
    model: Path = typer.Option(
        ...,
        "--model",
        "-m",
        help="Input ONNX model path",
    ),
    model_type: Optional[str] = typer.Option(
        None,
        "--type",
        help="mnist/mobilenetv2/resnet18/yolov5n, inferred when omitted",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Package output directory, default outputs/packages/<type>",
    ),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="Optional image/.npy/.bin/.txt/.csv used to create input.npy",
    ),
    model_json: Optional[Path] = typer.Option(
        None,
        "--json",
        help="Optional B-side JSON file",
    ),
    builtin_input: bool = typer.Option(
        True,
        "--builtin-input/--no-builtin-input",
        help="Generate built-in dummy input when --input is omitted",
    ),
):

    package_model(
        model_path=model,
        model_type=model_type,
        output_dir=output,
        input_path=input_file,
        model_json=model_json,
        builtin_input=builtin_input,
    )


@app.command("prepare-input-legacy")
def prepare_input_cmd(
    json_path: Path = typer.Option(
        ...,
        "--json",
        help="B-side model JSON / package model.json",
    ),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="Optional image/.npy/.bin/.txt/.csv",
    ),
    output: Path = typer.Option(
        Path("input.npy"),
        "--output",
        "-o",
    ),
    dummy: str = typer.Option(
        "zeros",
        "--dummy",
        help="zeros/ones/range when --input is omitted",
    ),
):

    create_input_npy(
        json_path=json_path,
        output_path=output,
        image_path=input_file,
        dummy_mode=dummy,
    )

@app.command("model-info")
def model_info(
    model: Path = typer.Option(
        ...,
        "--model"
    )
):

    print(
        get_model_info(model)
    )
@app.command("om-convert")
def om_convert(
    model: Path = typer.Option(
        ...,
        "--model",
        "-m"
    ),
    output_dir: Path = typer.Option(
        Path("outputs/om"),
        "--output-dir",
        "-o"
    ),
    soc_version: str = typer.Option(
        "Ascend310B4",
        "--soc-version"
    ),
    model_json: Optional[Path] = typer.Option(
        None,
        "--json",
        help="Optional B-side JSON / model.json",
    ),
    input_format: Optional[str] = typer.Option(
        None,
        "--input-format",
        help="Override ATC input_format. Omit this to use model.json.",
    ),
    input_shape: Optional[str] = typer.Option(
        None,
        "--input-shape",
        help="Override ATC shape, e.g. Input3:1,1,28,28",
    ),
    atc_args: Optional[str] = typer.Option(
        None,
        "--atc-args",
        help="Extra ATC args as one quoted string",
    ),
    timeout: int = typer.Option(
        600,
        "--timeout",
    ),
):

    result = convert_onnx_to_om(
        model_path=model,
        output_dir=output_dir,
        soc_version=soc_version,
        input_format=input_format,
        model_json=model_json,
        input_shape=input_shape,
        extra_args=shlex.split(atc_args) if atc_args else None,
        timeout=timeout,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

@app.command("board-sync")
def board_sync_cmd(

    host: str = typer.Option(
        ...,
        "--host"
    ),

    package_dir: Optional[Path] = typer.Option(
        None,
        "--package",
        help="Package dir generated by edgeai package",
    ),

    model_name: Optional[str] = typer.Option(
        None,
        "--model-name"
    ),

    user: str = typer.Option(
        "HwHiAiUser",
        "--user"
    ),

    remote_root: str = typer.Option(
        "~/edgeai_models",
        "--remote-root",
    ),

    min_free_gb: float = typer.Option(
        2.0,
        "--min-free-gb",
    ),

):

    board_sync(

        package_dir=package_dir,

        host=host,

        model_name=model_name,

        user=user,

        remote_root=remote_root,

        min_free_gb=min_free_gb,
    )


@app.command("board-run")
def board_run_cmd(
    host: str = typer.Option(
        ...,
        "--host",
    ),
    package_dir: Optional[Path] = typer.Option(
        None,
        "--package",
        help="Local package dir, default outputs/packages/<model-name>",
    ),
    model_name: Optional[str] = typer.Option(
        None,
        "--model-name",
    ),
    user: str = typer.Option(
        "HwHiAiUser",
        "--user",
    ),
    port: int = typer.Option(
        7891,
        "--port",
        "-p",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Local dir to pull board results into; defaults to package dir",
    ),
    remote_root: str = typer.Option(
        "~/edgeai_models",
        "--remote-root",
    ),
    wait: float = typer.Option(
        3.0,
        "--wait",
        "-w",
    ),
    force_convert: bool = typer.Option(
        False,
        "--force-convert/--no-force-convert",
        help="Reuse existing model.om by default; pass --force-convert to rebuild OM.",
    ),
):

    board_run(
        host=host,
        model_name=model_name,
        port=port,
        output_dir=output,
        package_dir=package_dir,
        user=user,
        remote_root=remote_root,
        wait=wait,
        force_convert=force_convert,
    )


@app.command("board-deploy")
def board_deploy_cmd(
    model: Path = typer.Option(
        ...,
        "--model",
        "-m",
        help="Input ONNX model path",
    ),
    host: str = typer.Option(
        ...,
        "--host",
    ),
    model_type: Optional[str] = typer.Option(
        None,
        "--type",
        help="mnist/mobilenetv2/resnet18/yolov5n, inferred when omitted",
    ),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="Optional image/.npy/.bin/.txt/.csv used to create input.npy",
    ),
    model_json: Optional[Path] = typer.Option(
        None,
        "--json",
        help="Optional B-side JSON file",
    ),
    package_output: Optional[Path] = typer.Option(
        None,
        "--package-output",
        help="Local package output directory",
    ),
    user: str = typer.Option(
        "HwHiAiUser",
        "--user",
    ),
    port: int = typer.Option(
        7891,
        "--port",
        "-p",
    ),
    remote_root: str = typer.Option(
        "~/edgeai_models",
        "--remote-root",
    ),
    wait: float = typer.Option(
        3.0,
        "--wait",
        "-w",
    ),
    min_free_gb: float = typer.Option(
        2.0,
        "--min-free-gb",
    ),
    force_convert: bool = typer.Option(
        False,
        "--force-convert/--no-force-convert",
        help="Reuse existing model.om by default; pass --force-convert to rebuild OM.",
    ),
    update_matrix: bool = typer.Option(
        True,
        "--matrix/--no-matrix",
        help="Regenerate outputs/model_matrix/matrix.json after board run",
    ),
):

    package_path = package_model(
        model_path=model,
        model_type=model_type,
        output_dir=package_output,
        input_path=input_file,
        model_json=model_json,
        builtin_input=True,
    )

    remote_dir = board_sync(
        package_dir=package_path,
        host=host,
        model_name=model_type,
        user=user,
        remote_root=remote_root,
        min_free_gb=min_free_gb,
    )

    board_run(
        host=host,
        model_name=model_type,
        port=port,
        output_dir=package_path,
        package_dir=package_path,
        user=user,
        remote_root=remote_root,
        remote_dir=remote_dir,
        wait=wait,
        force_convert=force_convert,
    )

    if update_matrix:
        generate_matrix()

@app.command("matrix-report")
def matrix_report_cmd(
    markdown_output: Path = typer.Option(
        Path("reports/model_matrix.md"),
        "--markdown-output",
    ),
    html_output: Path = typer.Option(
        Path("reports/model_matrix.html"),
        "--html-output",
    ),
):
    """Generate model matrix Markdown + HTML reports from matrix.json."""
    generate_matrix_reports(
        markdown_output=markdown_output,
        html_output=html_output,
    )

@app.command("pc-aipro-report")
def pc_aipro_report_cmd(
    matrix: Path = typer.Option(
        Path("outputs/model_matrix/matrix.json"),
        "--matrix",
    ),
    markdown_output: Path = typer.Option(
        Path("reports/pc_aipro_compare.md"),
        "--markdown-output",
    ),
    html_output: Path = typer.Option(
        Path("reports/pc_aipro_compare.html"),
        "--html-output",
    ),
):
    """Generate PC vs OrangePi AIPro comparison reports from matrix.json."""
    generate_pc_aipro_reports(
        matrix_path=matrix,
        markdown_output=markdown_output,
        html_output=html_output,
    )




@app.command("convert")
def convert_cmd(
    source_model: Path = typer.Option(
        ...,
        "--source-model",
        "-s",
        help="User-trained source model: .onnx/.pt/.pth/SavedModel/.h5/.keras/.pb/.pkl/.joblib/...",
    ),
    framework: str = typer.Option(
        "auto",
        "--framework",
        "-f",
        help="auto/onnx/pytorch/torchscript/tensorflow/sklearn/xgboost/lightgbm",
    ),
    package_name: Optional[str] = typer.Option(
        None,
        "--package",
        "-p",
        help="Output package name under outputs/packages/<name>",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Optional explicit output package directory",
    ),
    opset: int = typer.Option(11, "--opset", help="ONNX opset version"),
    input_shape: Optional[str] = typer.Option(
        None,
        "--input-shape",
        help="Model input shape. Example: 1,3,224,224. PyTorch conversion will prompt if missing.",
    ),
    input_name: str = typer.Option("input", "--input-name", help="ONNX input name"),
    output_name: str = typer.Option("output", "--output-name", help="ONNX output name"),
    arch: Optional[str] = typer.Option(
        None,
        "--arch",
        help="Model architecture for PyTorch state_dict. Example: torchvision:shufflenet_v2_x1_0",
    ),
    feature_count: Optional[int] = typer.Option(
        None,
        "--feature-count",
        help="Feature count for sklearn/xgboost/lightgbm models. Example: 4",
    ),
    torchscript: bool = typer.Option(
        False,
        "--torchscript/--no-torchscript",
        help="Treat PyTorch .pt as TorchScript model",
    ),
    dynamic_batch: bool = typer.Option(
        True,
        "--dynamic-batch/--static-batch",
        help="Export dynamic batch axis when supported",
    ),
    interactive: Optional[bool] = typer.Option(
        None,
        "--interactive/--no-interactive",
        help="Prompt for missing parameters in terminal. Default: auto-detect TTY.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite/--no-overwrite",
        help="Remove existing package directory before conversion",
    ),
):
    """Convert/import a user-trained model to an ONNX package with guided parameter completion."""
    import json as _json
    from .convert_model import convert_model

    try:
        result = convert_model(
            source_model=source_model,
            framework=framework,
            package_name=package_name,
            output_dir=output_dir,
            opset=opset,
            input_shape=input_shape,
            input_name=input_name,
            output_name=output_name,
            torchscript=torchscript,
            arch=arch,
            feature_count=feature_count,
            dynamic_batch=dynamic_batch,
            interactive=interactive,
            overwrite=overwrite,
        )
        typer.echo(_json.dumps(result, indent=2, ensure_ascii=False))
        # EDGEAI_CONVERT_ARTIFACT_VALIDATION: ok:false must fail the process.
        if isinstance(result, dict) and result.get("ok") is False:
            raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


@app.command("ui")
def ui_cmd(
    host: str = typer.Option("0.0.0.0", "--host", help="WebUI listening host"),
    port: int = typer.Option(8501, "--port", help="WebUI listening port"),
):
    """Launch EdgeAI-DeployKit WebUI."""
    import subprocess
    import sys

    project_root = Path(__file__).resolve().parents[1]
    app_path = project_root / "webui" / "app.py"

    if not app_path.exists():
        typer.echo(f"[ERROR] WebUI app not found: {app_path}")
        raise typer.Exit(code=1)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        host,
        "--server.port",
        str(port),
    ]

    raise typer.Exit(subprocess.call(cmd))

# ---------------------------------------------------------------------------
# EdgeAI Local Task System commands
# ---------------------------------------------------------------------------
@app.command("task-init")
def task_init_cmd(
    package: Path = typer.Option(..., "--package", help="Package name or outputs/packages/<name> path"),
    task_type: str = typer.Option("auto", "--task-type", help="auto/digit_classification/image_classification/object_detection/segmentation/text_classification/llm_chat"),
    label_map: Optional[Path] = typer.Option(None, "--label-map", help="Optional label map file"),
    label_language: str = typer.Option("zh", "--label-language", help="Label language, default zh"),
):
    from .task_system import create_or_update_model_task
    import json as _json
    result = create_or_update_model_task(package, task_type=task_type, label_map=label_map, label_language=label_language)
    print(_json.dumps(result, ensure_ascii=False, indent=2))

@app.command("task-info")
def task_info_cmd(
    package: Path = typer.Option(..., "--package", help="Package name or outputs/packages/<name> path"),
    auto_create: bool = typer.Option(False, "--auto-create/--no-auto-create", help="Create model_task.json when missing"),
):
    from .task_system import read_model_task
    import json as _json
    result = read_model_task(package, auto_create=auto_create)
    print(_json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
