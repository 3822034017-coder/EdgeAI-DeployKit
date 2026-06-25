# EdgeAI-DeployKit 项目介绍

## 项目简介

EdgeAI-DeployKit 是一个面向本地 AI 模型部署的跨平台工具包。项目提供 WebUI 图形界面和本地推理后端，用户可以上传自己训练好的模型，工具自动识别模型类型、完成模型转换或导入、生成本地部署 package，并根据任务类型提供对应的测试输入和结果展示。

项目目标是降低 AI 模型从训练到本地部署验证的门槛，让用户不需要手动编写复杂推理脚本，也能在 Windows、macOS、Linux x86_64、Linux arm64 等平台上完成模型部署、测试和报告导出。

## 项目能做什么

EdgeAI-DeployKit 当前主要支持以下能力：

1. 模型上传与识别  
   用户可以通过 WebUI 上传模型文件，工具会自动识别模型来源和类型，例如 ONNX、PyTorch、TensorFlow/Keras、传统机器学习模型、GGUF 大语言模型等。

2. 模型转换与本地部署包生成  
   支持将模型转换或导入为本地可运行的 package，生成 `model.onnx`、`model_signature.json`、`model_task.json` 等部署文件。

3. 本地推理  
   使用 ONNX Runtime CPU 在本机执行推理，不依赖外部服务器。用户上传测试图片或文本后，工具自动完成输入预处理、推理、结果解析和可视化。

4. 按任务类型展示结果  
   - 数字识别：提示用户上传数字图片，输出识别数字。
   - 图像分类：提示用户上传实物图片，输出 TopK 分类结果。
   - YOLO/目标检测：输入图片，输出带检测框的结果图。
   - 大语言模型：面向 GGUF 模型提供本地对话交互流程。

5. 报告生成  
   每次本地推理后会生成 Markdown、HTML、PDF 报告，包含模型信息、输入输出、推理结果、TopK 可视化、运行耗时等内容。

6. 跨平台软件包发布  
   项目已提供 Windows、macOS、Linux x86_64、Linux arm64 的 release 软件包，用户可以按系统下载对应压缩包使用。

## 支持的平台

当前提供以下平台的软件包：

| 平台 | 软件包 |
| --- | --- |
| Windows x86_64 | `EdgeAI-DeployKit-windows-x86_64.zip` |
| macOS Apple Silicon | `EdgeAI-DeployKit-macos-arm64.tar.gz` |
| macOS Intel | `EdgeAI-DeployKit-macos-x86_64.tar.gz` |
| Linux x86_64 | `EdgeAI-DeployKit-linux-x86_64.tar.gz` |
| Linux arm64 | `EdgeAI-DeployKit-linux-arm64.tar.gz` |

## 支持的模型类型

项目当前覆盖的模型类型包括：

- ONNX 模型：`.onnx`
- PyTorch 模型：`.pt`、`.pth`、`.ckpt`
- TensorFlow/Keras 模型：`.h5`、`.hdf5`、`.keras`、SavedModel、`.pb`、`.tflite`
- 传统机器学习模型：Scikit-learn、XGBoost、LightGBM
- 大语言模型：GGUF

不同模型类型需要的可选依赖不同。基础包支持 ONNX 导入和 ONNX Runtime 本地推理；PyTorch、TensorFlow、传统机器学习、大语言模型等能力会按需安装或提示用户补充依赖。

## 使用流程

典型使用流程如下：

1. 下载对应系统的软件包并解压。
2. 启动 WebUI。
3. 上传用户自己的模型文件。
4. 工具自动识别模型类型和任务类型。
5. 根据提示上传测试输入，例如图片或文本。
6. 执行本地推理。
7. 查看可视化结果。
8. 导出 Markdown/PDF 报告。

## Windows 使用方式

下载并解压 Windows 软件包后，双击：

```text
start-windows.bat
```

如果电脑缺少 Python，可以双击：

```text
install-runtime-windows.bat
```

启动后浏览器访问：

```text
http://127.0.0.1:3000/workspace
```

停止服务：

```text
stop-windows.bat
```

## macOS 使用方式

Apple Silicon Mac 下载 `macos-arm64` 包，Intel Mac 下载 `macos-x86_64` 包。

解压后执行：

```bash
./install-macos.sh
./start-macos.sh
```

停止服务：

```bash
./start-macos.sh stop
```

## Linux 使用方式

解压后执行：

```bash
./install-linux.sh
./start-linux.sh
```

如果是在虚拟机中，希望宿主机访问 WebUI，可以使用：

```bash
./start-linux.sh --lan
```

停止服务：

```bash
./start-linux.sh stop
```

## 开源地址

GitHub 开源仓库：

https://github.com/HaoWenXinme/EdgeAI-DeployKit

## 软件包下载地址

Release 页面：

https://github.com/HaoWenXinme/EdgeAI-DeployKit/releases/tag/v0.2.0-local-preview

各平台直接下载地址：

- Windows x86_64  
  https://github.com/HaoWenXinme/EdgeAI-DeployKit/releases/download/v0.2.0-local-preview/EdgeAI-DeployKit-windows-x86_64.zip

- macOS Apple Silicon arm64  
  https://github.com/HaoWenXinme/EdgeAI-DeployKit/releases/download/v0.2.0-local-preview/EdgeAI-DeployKit-macos-arm64.tar.gz

- macOS Intel x86_64  
  https://github.com/HaoWenXinme/EdgeAI-DeployKit/releases/download/v0.2.0-local-preview/EdgeAI-DeployKit-macos-x86_64.tar.gz

- Linux x86_64  
  https://github.com/HaoWenXinme/EdgeAI-DeployKit/releases/download/v0.2.0-local-preview/EdgeAI-DeployKit-linux-x86_64.tar.gz

- Linux arm64  
  https://github.com/HaoWenXinme/EdgeAI-DeployKit/releases/download/v0.2.0-local-preview/EdgeAI-DeployKit-linux-arm64.tar.gz

## 项目特点

- WebUI 图形化操作，降低模型部署门槛。
- 支持多种模型格式和任务类型。
- 支持本地推理，不依赖云端服务。
- 支持 Windows、macOS、Linux 多平台发布。
- 自动生成部署 package 和推理报告。
- 适合作为模型本地部署、课程项目、比赛作品、边缘 AI 工具链原型使用。

## 当前状态

项目当前处于本地部署工具包预览版本阶段，核心本地推理流程已经跑通。后续可以继续完善完整离线包、更多模型自动适配、macOS 真机验证、Linux arm64 真机验证以及大语言模型交互体验。
