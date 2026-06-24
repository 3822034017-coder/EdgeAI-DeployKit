from pathlib import Path
import os
import onnx


def get_shape(value_info):

    dims = []

    for d in value_info.type.tensor_type.shape.dim:

        if d.dim_value:

            dims.append(d.dim_value)

        else:

            dims.append("?")

    return dims


def get_model_info(model_path):

    model = onnx.load(str(model_path))

    initializers = {
        item.name
        for item in model.graph.initializer
    }

    real_inputs = []

    input_shapes = {}

    for item in model.graph.input:

        if item.name not in initializers:

            real_inputs.append(item.name)

            input_shapes[item.name] = get_shape(item)

    return {

        "model":
        Path(model_path).stem,

        "size_mb":
        round(
            os.path.getsize(model_path)
            / (1024 * 1024),
            2
        ),

        "inputs":
        real_inputs,

        "input_shapes":
        input_shapes,

        "outputs":
        [
            o.name
            for o in model.graph.output
        ]
    }
