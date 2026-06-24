# Convert Smart Wizard Guide

## CLI 推荐用法

```bash
edgeai convert \
  --framework auto \
  --source-model inputs/models/shufflenetv2.pth \
  --package shufflenetv2_local \
  --opset 11 \
  --overwrite
```

如果缺少参数，命令行会提示：

- `input_shape`：例如 `1,3,224,224`
- `arch`：例如 `torchvision:shufflenet_v2_x1_0`
- `feature_count`：例如 `4`
- `input_name` / `output_name`：GraphDef `.pb` 需要

## WebUI 推荐用法

Pipeline → 01 Upload / Convert Model → 上传模型 → 点击“检测并转换为 ONNX Package”。

如果参数不足，会出现 Convert Wizard 弹窗。补齐后点击“补齐参数并开始转换”。
