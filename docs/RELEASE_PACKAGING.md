# EdgeAI-DeployKit Release Packaging

## Goal

EdgeAI-DeployKit is moving from a board-first prototype to a cross-platform local
deployment toolkit. The GitHub Release package should let a user open the WebUI,
upload a trained model, convert or import it into an ONNX package, run local
inference, view task-aware results, and export Markdown/PDF reports.

Supported release targets:

- `windows-x86_64`
- `macos-x86_64`
- `macos-arm64`
- `linux-x86_64`
- `linux-arm64`

## Build

Build the current host package:

```bash
python release/build_release.py
```

Build all platform-named source packages:

```bash
python release/build_release.py --target all
```

Artifacts are written under `release_dist/` as:

- `EdgeAI-DeployKit-windows-x86_64.zip`
- `EdgeAI-DeployKit-macos-x86_64.tar.gz`
- `EdgeAI-DeployKit-macos-arm64.tar.gz`
- `EdgeAI-DeployKit-linux-x86_64.tar.gz`
- `EdgeAI-DeployKit-linux-arm64.tar.gz`

## What Is Included

- `product-ui/` Next.js product WebUI
- `backend/` FastAPI local service
- `edgeai/` CLI, conversion, local inference, task system, report code
- `scripts/` setup and helper scripts
- `models/`, `examples/`, `templates/`, `configs/`, `docs/`
- `README.md`, `README_PRODUCT_UI.md`, and `RELEASE_NOTES.md`
- platform launcher scripts
  - Windows: `start-windows.bat`, `stop-windows.bat`, `scripts/start-windows.ps1`
  - Linux/macOS: shell launchers

## What Is Excluded

The package builder intentionally excludes generated and heavy artifacts:

- `outputs/`
- `reports/`
- `node_modules/`
- `.next/`
- `.venv/`
- `third_party/`
- backup files and backup directories
- TypeScript build info files
- model weights and exported model files such as `.onnx`, `.pt`, `.pth`, `.h5`
- QEMU/rootfs build products

These files should be downloaded, generated, or uploaded by the user at runtime.

## Runtime Path

The local deployment path is:

```text
Convert -> Analyze -> Task Init -> Prepare Input -> Local Run -> Task Render -> Report
```

The backend now uses the current Python runtime to execute:

```bash
python -m edgeai.cli ...
```

This avoids relying on a globally installed `edgeai` command and makes the same
code path usable from Windows, macOS, Linux x86_64, and Linux arm64 release
packages.
