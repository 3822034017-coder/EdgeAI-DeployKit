# macOS Local Release Guide

This guide covers:

- `EdgeAI-DeployKit-macos-x86_64.tar.gz` for Intel Macs
- `EdgeAI-DeployKit-macos-arm64.tar.gz` for Apple Silicon Macs

## Prerequisites

- macOS 12 or newer is recommended.
- Python 3.10+ on `PATH`. Python 3.10-3.12 is recommended for broad AI package compatibility.
- Node.js 20+ with Corepack, or a global `pnpm`.
- Network access to Python/npm package indexes on first install.

Recommended Homebrew setup:

```bash
brew install python@3.12 node
corepack enable
```

## Quick Start

Extract the package:

```bash
tar -xzf EdgeAI-DeployKit-macos-arm64.tar.gz
cd EdgeAI-DeployKit-macos-arm64
```

For Intel Macs, use:

```bash
tar -xzf EdgeAI-DeployKit-macos-x86_64.tar.gz
cd EdgeAI-DeployKit-macos-x86_64
```

Install runtime dependencies:

```bash
./install-macos.sh
```

Start the backend and WebUI:

```bash
./start-macos.sh
```

The browser opens:

```text
http://127.0.0.1:3000/workspace
```

Stop both services:

```bash
./start-macos.sh stop
```

Check service status:

```bash
./start-macos.sh status
```

## Optional Model Adapter Dependencies

For PyTorch `.pt` / `.pth` conversion support:

```bash
./install-macos.sh --with-pytorch
```

For TensorFlow/Keras conversion support:

```bash
./install-macos.sh --with-tensorflow
```

For scikit-learn / XGBoost / LightGBM conversion support:

```bash
./install-macos.sh --with-ml
```

For GGUF LLM chat support:

```bash
./install-macos.sh --with-llm
```

## Notes

- The macOS packages are lightweight source-portable packages. They create `.venv`
  and install WebUI dependencies on first run.
- Generated packages and reports are written under `outputs/packages/`.
- Apple Silicon users should prefer `macos-arm64`; Intel users should prefer
  `macos-x86_64`.
- If Gatekeeper warns about scripts from the internet, run them from Terminal
  after extracting the archive.
