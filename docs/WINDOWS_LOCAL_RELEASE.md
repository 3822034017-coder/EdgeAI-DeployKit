# Windows Local Release Guide

This guide covers the Windows x86_64 zip package:

```text
EdgeAI-DeployKit-windows-x86_64.zip
```

## Prerequisites

The zip package is source-portable and installs runtime dependencies on first
start. The machine needs:

- Windows 10/11 x86_64
- Python 3.9-3.13. Python 3.10-3.12 is recommended for best AI package compatibility.
- Node.js 20+ with Corepack, or a global `pnpm`

## Quick Start

Extract the zip, then double-click:

```text
start-windows.bat
```

The first run will:

1. Create `.venv`
2. Install Python dependencies
3. Install WebUI dependencies
4. Start the FastAPI backend
5. Start the Next.js WebUI
6. Open `http://127.0.0.1:3000/workspace`

Stop both local services:

```text
stop-windows.bat
```

## Optional Framework Dependencies

For PyTorch `.pt` / `.pth` conversion support:

```powershell
.\start-windows.bat -WithPytorch
```

For TensorFlow/Keras conversion support:

```powershell
.\start-windows.bat -WithTensorflow
```

For both:

```powershell
.\start-windows.bat -WithPytorch -WithTensorflow
```

## Useful Parameters

Run from PowerShell:

```powershell
.\start-windows.bat -ApiPort 8010 -UiPort 3010
.\start-windows.bat -NoBrowser
.\start-windows.bat -NoInstall
```

Logs are written under:

```text
outputs/logs/
```

PID and port files are written under:

```text
outputs/pids/
```

## Notes

- The package does not bundle model weights, generated ONNX files, `.venv`,
  `node_modules`, or reports.
- Users upload their own trained models from the WebUI.
- Generated local inference packages are written under
  `outputs/packages/<package_name>/`.
