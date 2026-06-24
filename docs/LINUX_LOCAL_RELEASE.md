# Linux Local Release Guide

This guide covers the Linux x86_64 and Linux arm64 release path for
EdgeAI-DeployKit.

## Package Targets

- `EdgeAI-DeployKit-linux-x86_64.tar.gz`
- `EdgeAI-DeployKit-linux-arm64.tar.gz`

Build both from the project root:

```bash
python release/build_release.py --target linux-x86_64
python release/build_release.py --target linux-arm64
```

## Install On Linux

After extracting a release package:

```bash
./install-linux.sh
```

For TensorFlow/Keras H5, `.keras`, and SavedModel conversion:

```bash
./install-linux.sh --with-tensorflow
```

For PyTorch `.pt` / `.pth` conversion:

```bash
./install-linux.sh --with-pytorch
```

For both optional framework conversion stacks:

```bash
./install-linux.sh --with-pytorch --with-tensorflow
```

The installer creates `.venv`, installs the Python backend and CLI, installs the
product UI dependencies when pnpm/Corepack is available, and writes:

```text
outputs/linux_doctor.json
```

## Start

For a single-machine Linux desktop:

```bash
./start-linux.sh
```

For a VMware/openEuler VM that you want to access from the host machine:

```bash
./start-linux.sh --lan
```

This starts the FastAPI backend and Next.js WebUI in the background, writes logs
to `outputs/logs/`, and prints the URL to open.

Stop both services:

```bash
./start-linux.sh stop
```

Check service state:

```bash
./start-linux.sh status
```

You can still run the backend and UI manually if you prefer separate terminals.

Terminal 1:

```bash
./start-backend.sh
```

Terminal 2:

```bash
./start-ui.sh
```

Then open:

```text
http://127.0.0.1:3000
```

## Local Inference Flow

The Linux product path is:

```text
Upload/Convert -> Analyze -> Task Init -> Upload Test Input -> Local Run -> Task Render -> Report
```

The backend executes CLI work through:

```bash
python -m edgeai.cli
```

This avoids relying on a globally installed `edgeai` command and keeps the Linux
release package self-contained around its `.venv`.

## Doctor

Run:

```bash
python scripts/linux_doctor.py --json outputs/linux_doctor.json
```

Required modules for the default local ONNX path:

- `typer`
- `pydantic`
- `fastapi`
- `uvicorn`
- `onnx`
- `onnxruntime`
- `numpy`
- `PIL`

Optional modules:

- TensorFlow/Keras conversion: `tensorflow`, `tf2onnx`, `h5py`
- PyTorch conversion: `torch`, `torchvision`
- sklearn / booster conversion: `skl2onnx`, `onnxmltools`

## Release Smoke Test

The Linux x86_64 release package has been smoke-tested on openEuler 24.03 in
VMware:

- extracted `EdgeAI-DeployKit-linux-x86_64.tar.gz` into a clean directory
- ran `./install-linux.sh --no-frontend`
- started with `./start-linux.sh --lan --api-port 8021 --ui-port 3021`
- verified WebUI `/workspace` and backend `/api/health`
- uploaded an ONNX ShuffleNetV2 model and a dog image through the backend API
- ran `local-model-setup`
- ran the full local inference flow
- generated `task_result.json`, `local_topk_result.png`, `report.md`, and `report.pdf`
- verified package-local PDF download through the WebUI proxy

The generated TopK PNG was visually checked and CJK labels rendered correctly.

## openEuler Notes

On openEuler, install Python 3.9+ and Node.js 20+ before running the installer.
If Node/Corepack is not available, the backend and CLI can still run, but the
Next.js product UI will need frontend dependencies installed later.

The Orange Pi / board path is kept as an advanced route. The default Linux
release workflow is local inference on ONNX Runtime CPU.
