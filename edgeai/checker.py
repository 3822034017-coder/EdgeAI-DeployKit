from pathlib import Path
import os
import onnx


def check_model(model_path):

    model = onnx.load(str(model_path))

    onnx.checker.check_model(model)

    initializers = {
        item.name
        for item in model.graph.initializer
    }

    real_inputs = []

    for item in model.graph.input:

        if item.name not in initializers:

            real_inputs.append(item.name)

    print("=" * 60)

    print("ONNX CHECK PASSED")

    print("=" * 60)

    print(
        f"Model : {Path(model_path).name}"
    )

    print(
        f"Size  : "
        f"{os.path.getsize(model_path)/(1024*1024):.2f} MB"
    )

    print()

    print("Inputs:")

    for item in real_inputs:

        print(f"  - {item}")

    print()

    print("Outputs:")

    for item in model.graph.output:

        print(f"  - {item.name}")
