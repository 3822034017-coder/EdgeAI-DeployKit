# EdgeAI-DeployKit Convert Foundation 使用说明

这个补丁新增 `edgeai convert`，用于把用户训练模型导入到 `outputs/packages/<package>/model.onnx`，然后复用已经跑通的本地推理闭环：

```text
convert → analyze → prepare-input → local-run → report
```

## 支持范围

第一版以稳定为主：

| framework | 支持情况 |
|---|---|
| onnx | 直接导入、ONNX checker 校验 |
| tensorflow | SavedModel / .h5 / .keras / .pb，依赖 tf2onnx |
| pytorch | TorchScript 或完整 nn.Module，依赖 torch；state_dict 需要模型结构代码，第一版会给兼容性报告 |
| sklearn | 依赖 skl2onnx/joblib |
| xgboost | 依赖 xgboost/onnxmltools |
| lightgbm | 依赖 lightgbm/onnxmltools |

## ONNX 导入示例

```bash
cd /root/edge-ai-deploy-kit
source .venv/bin/activate

edgeai convert \
  --framework onnx \
  --source-model models/zoo/mobilenetv2/model.onnx \
  --package mobilenetv2_convert_local \
  --overwrite

edgeai analyze --package outputs/packages/mobilenetv2_convert_local
edgeai prepare-input --package outputs/packages/mobilenetv2_convert_local --input photo/cat.png
edgeai local-run --package outputs/packages/mobilenetv2_convert_local
edgeai report --package outputs/packages/mobilenetv2_convert_local
```

## TensorFlow 示例

```bash
pip install tf2onnx tensorflow

edgeai convert \
  --framework tensorflow \
  --source-model /path/to/saved_model_dir \
  --package tf_model_local \
  --opset 11 \
  --overwrite
```

## PyTorch TorchScript 示例

```bash
pip install torch

edgeai convert \
  --framework pytorch \
  --source-model /path/to/model.pt \
  --package torch_model_local \
  --input-shape 1,3,224,224 \
  --torchscript \
  --opset 11 \
  --overwrite
```

如果 `.pth` 只是 `state_dict`，转换会失败并生成：

```text
outputs/packages/<package>/compatibility_report.md
outputs/packages/<package>/convert_result.json
```

这是正常现象，因为仅权重文件没有网络结构，不能独立导出 ONNX。
