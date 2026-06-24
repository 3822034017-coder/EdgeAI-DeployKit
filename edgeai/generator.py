from pathlib import Path
import shutil

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def generate_demo(model_path: Path, output_dir: Path) -> None:
    """
    Generate a lightweight C++ demo project.

    Inputs:
        model_path: ONNX model path, for example outputs/model_int8.onnx
        output_dir: generated C++ demo directory, for example outputs/infer_demo

    Outputs:
        output_dir/infer.cpp
        output_dir/CMakeLists.txt
        output_dir/<model_name>
    """
    model_path = Path(model_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    project_root = Path(__file__).resolve().parents[1]
    template_dir = project_root / "templates" / "classification"

    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    context = {
        "model_name": model_path.name,
    }

    files = {
        "infer.cpp.j2": "infer.cpp",
        "CMakeLists.txt.j2": "CMakeLists.txt",
    }

    for template_name, output_name in files.items():
        template = env.get_template(template_name)
        rendered = template.render(**context)
        (output_dir / output_name).write_text(rendered, encoding="utf-8")

    copied_model = output_dir / model_path.name
    if copied_model.resolve() != model_path:
        shutil.copy2(model_path, copied_model)

    print("C++ demo generated successfully.")
    print(f"Output directory: {output_dir}")
    print("Generated files:")
    print(f"  - {output_dir / 'infer.cpp'}")
    print(f"  - {output_dir / 'CMakeLists.txt'}")
    print(f"  - {copied_model}")
