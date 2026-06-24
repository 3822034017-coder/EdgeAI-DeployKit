# EdgeAI-DeployKit Release Notes

## Linux Local Release Candidate

Date: 2026-06-24

This release candidate focuses on the Linux local inference product path:

```text
Upload / Convert -> Analyze -> Task Init -> Prepare Input -> Local Run -> Task Render -> Report
```

## Highlights

- Added Linux release archives for `linux-x86_64` and `linux-arm64`.
- Added root-level `install-linux.sh` and `start-linux.sh` launch flow.
- Added `--lan`, custom API/UI ports, `status`, and `stop` support to the Linux starter.
- Added task-aware local inference results for classification-style models.
- Added Chinese ImageNet label overrides with English fallback labels.
- Fixed TopK report image rendering by using CJK-capable fonts when needed.
- Added Markdown/PDF report generation from package-local artifacts.
- Added package-cleaning rules so release archives exclude backup files, caches,
  model weights, generated outputs, reports, and frontend build artifacts.
- Added optional install switches:
  - `./install-linux.sh --with-pytorch`
  - `./install-linux.sh --with-tensorflow`

## Validated On Linux x86_64

Environment:

- openEuler 24.03 LTS-SP3
- Linux x86_64
- Python 3.11
- Node.js 20
- pnpm 10

Validated release package flow:

- Extract `EdgeAI-DeployKit-linux-x86_64.tar.gz`.
- Run `./install-linux.sh --no-frontend`.
- Run `./start-linux.sh --lan --api-port 8021 --ui-port 3021`.
- Verify WebUI `/workspace` returns HTTP 200.
- Upload ONNX model and image through the backend API.
- Run `local-model-setup`.
- Run local ONNX Runtime CPU inference.
- Generate `task_result.json`, `local_topk_result.png`, `report.md`, and `report.pdf`.
- Verify PDF proxy download returns `application/pdf`.

Validated sample result:

- Model: ShuffleNetV2 ONNX package
- Input: dog image
- Task: image classification
- Top1: `kuvasz` / `库瓦兹犬`

## Known Notes

- PyTorch conversion needs optional `torch` and `torchvision` dependencies.
  Use `./install-linux.sh --with-pytorch`.
- TensorFlow/Keras conversion needs optional `tensorflow-cpu`, `tf2onnx`, and
  `h5py`. Use `./install-linux.sh --with-tensorflow`.
- First-time PyTorch installation can be slow or network-sensitive because the
  wheel is large. The Linux installer uses the PyTorch CPU wheel index by
  default and can be overridden with `PYTORCH_INDEX_URL`.
- Linux arm64 packages are generated but still need runtime validation on an
  arm64 Linux system.
- Windows x86_64 packaging is available as `EdgeAI-DeployKit-windows-x86_64.zip`
  with `start-windows.bat` and `stop-windows.bat`; full Windows runtime
  validation is in progress.
- macOS launchers are scaffolded; full runtime validation is pending.

## Generated Artifacts

Release archives are generated under:

```text
release_dist/
```

Current package names:

- `EdgeAI-DeployKit-linux-x86_64.tar.gz`
- `EdgeAI-DeployKit-linux-arm64.tar.gz`
- `EdgeAI-DeployKit-windows-x86_64.zip`
