from pathlib import Path

from onnxruntime.quantization import (
    QuantType,
    quantize_dynamic,
)


def quantize_model(
    model_path: Path,
    output_path: Path,
) -> None:
    """
    Convert FP32 ONNX model to INT8 ONNX model
    """

    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found: {model_path}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("===================================")
    print("Starting INT8 quantization")
    print("===================================")

    print(f"Input model : {model_path}")
    print(f"Output model: {output_path}")

    quantize_dynamic(
        model_input=str(model_path),
        model_output=str(output_path),
        weight_type=QuantType.QInt8,
    )

    print("===================================")
    print("Quantization finished")
    print("===================================")

    print(f"INT8 model saved to: {output_path}")
