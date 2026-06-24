# EdgeAI Model Intelligence Registry

EdgeAI-DeployKit does not hard-code a fix for one model. The conversion pipeline now has a **model intelligence layer**:

1. Probe the uploaded model file.
2. Detect the framework/source kind.
3. For PyTorch `state_dict`/checkpoint files, read tensor names and shapes.
4. Match the fingerprint against `edgeai/model_registry/registry.json`.
5. Suggest or automatically try candidate `arch` values.
6. Convert to ONNX only after a candidate can be loaded and validated.

## Why this is necessary

A `.pth` file may contain only weights, not Python model code. In that case, no tool can fully reconstruct every custom network from the file alone. The best practical design is:

- Automatically match common architectures from a registry.
- Validate the match by loading weights and exporting ONNX.
- If no match exists, ask the user for the missing model architecture or adapter code.

## Example

```bash
edgeai model-probe \
  --source-model inputs/models/shufflenetv2.pth \
  --framework pytorch
```

For ShuffleNetV2 x0.5 state_dict, the registry should suggest:

```text
torchvision:shufflenet_v2_x0_5
```

## Extending the registry

Add new model entries to:

```text
edgeai/model_registry/registry.json
```

Recommended fields:

- `id`
- `framework`
- `family`
- `aliases`
- `input_shape`
- `task_type`
- `output_type`
- `preprocess_profile`
- `loader`
- `state_dict_signature`

Future extensions can add `timm`, YOLO, TensorFlow/Keras, sklearn, XGBoost, LightGBM, HuggingFace and GGUF profiles.
