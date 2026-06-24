# EdgeAI TensorFlow Universal Importer v1

This importer is a general TensorFlow/Keras entry layer for EdgeAI-DeployKit.
It is not a one-off conversion path for a single `.h5` file.

## Supported Inputs

- `.keras`: modern Keras model format. The importer loads it, exports a
  SavedModel when needed, and converts it to ONNX with `tf2onnx`.
- `.h5` / `.hdf5`: Keras H5 files. The importer first tries standard Keras
  loading. If that fails for older Sequential H5 files, it uses a fallback
  reconstruction path.
- SavedModel directory: detected by `saved_model.pb` and converted through the
  `tf2onnx` SavedModel path.
- Frozen Graph `.pb`: supported when the user provides input and output names.
- `.tflite`: best-effort conversion through `tf2onnx` TFLite support.
- TensorFlow checkpoints: detected but not directly converted because they
  usually contain variables without a complete graph.

## Usage

```bash
edgeai convert \
  --framework tensorflow \
  --source-model inputs/models/tensorflow/keras_mnist_model.h5 \
  --package keras_mnist_tf_local \
  --input-shape 1,28,28,1 \
  --input-name input \
  --output-name output \
  --opset 15 \
  --overwrite
```

Probe a TensorFlow/Keras model before conversion:

```bash
python scripts/edgeai_tf_probe.py \
  --source-model inputs/models/tensorflow/keras_mnist_model.h5 \
  --input-shape 1,28,28,1
```

## Design Principles

The importer follows this structure:

```text
container detection -> input/output probing -> route selection -> explicit repair hints
```

The legacy H5 fallback is only one branch of the importer. The main goal is to
provide a predictable TensorFlow/Keras import surface for the WebUI and CLI.

