# EdgeAI Product WebUI 操作指南

## 1. 文件放置位置

把压缩包内容解压到你的主工程根目录：

```bash
cd /root/edge-ai-deploy-kit
unzip edgeai-product-ui-productized.zip
```

解压后应出现：

```text
/root/edge-ai-deploy-kit/
├── product-ui/                 # Next.js 前端
├── backend/                    # FastAPI 后端
├── scripts/run-product-api.sh
├── scripts/run-product-web.sh
├── docker-compose.product.yml
└── README_PRODUCT_UI.md
```

原来的 `webui/app.py` 可以保留，不需要删除。新 UI 是独立产品层。

## 2. 需要的系统包

openEuler / Linux 上建议先装：

```bash
sudo dnf install -y python3 python3-pip nodejs npm gcc gcc-c++ make cmake git
```

如需完整部署链，还需要你原项目本来要求的：

```text
Docker
qemu-system-aarch64
openEuler aarch64 SDK
ONNX Runtime SDK
CANN / atc
SSH / SCP / sshpass
```

这些重依赖不是前端必需，但 QEMU、板端和 ATC 功能会用到。

## 3. Python 包

后端需要：

```bash
python3 -m pip install -r backend/requirements.txt
python3 -m pip install -e . --no-build-isolation
```

`backend/requirements.txt` 内容为：

```text
fastapi>=0.110
uvicorn[standard]>=0.29
pydantic>=2.6
python-multipart>=0.0.9
```

## 4. Node / 前端包

前端需要：

```bash
cd product-ui
npm install
```

主要依赖：

```text
next
react
react-dom
typescript
tailwindcss
postcss
autoprefixer
lucide-react
recharts
clsx
@types/node
@types/react
@types/react-dom
```

## 5. 开发启动

开两个终端。

终端 1：启动后端 API：

```bash
cd /root/edge-ai-deploy-kit
bash scripts/run-product-api.sh
```

或者手动：

```bash
cd /root/edge-ai-deploy-kit
python3 -m pip install -r backend/requirements.txt
python3 -m pip install -e . --no-build-isolation
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

终端 2：启动前端：

```bash
cd /root/edge-ai-deploy-kit
bash scripts/run-product-web.sh
```

或者手动：

```bash
cd /root/edge-ai-deploy-kit/product-ui
npm install
npm run dev
```

浏览器打开：

```text
http://localhost:3000
```

后端接口：

```text
http://localhost:8000/api/health
http://localhost:8000/api/dashboard
http://localhost:8000/docs
```

## 6. Docker Compose 启动

```bash
cd /root/edge-ai-deploy-kit
docker compose -f docker-compose.product.yml up --build
```

前端：

```text
http://localhost:3000
```

后端：

```text
http://localhost:8000/docs
```

## 7. 当前实现了什么

### 前端 `product-ui/`

- 产品级左侧导航
- 总览 KPI
- 模型注册表
- 部署流水线状态
- Benchmark 曲线视图
- 板端 / QEMU / Docker 状态卡
- 报告与产物列表
- 命令任务控制台
- 每 5 秒自动刷新后端状态
- 后端不可用时显示 fallback 数据，页面不会白屏

### 后端 `backend/`

- `/api/health`：检测 edgeai、python、cmake、gcc、qemu、atc、docker、aarch64 SDK
- `/api/models`：扫描 `models/`、`examples/`、`inputs/`、`outputs/` 里的 ONNX
- `/api/matrix`：读取 `outputs/model_matrix/matrix.json`
- `/api/artifacts`：扫描 reports、packages、benchmark、matrix 产物
- `/api/jobs`：创建和查询任务
- `/api/jobs/{id}/logs`：读取任务日志
- `/api/uploads/{kind}`：上传模型、图片、JSON、输入文件

任务日志会放在：

```text
outputs/jobs/<job_id>/meta.json
outputs/jobs/<job_id>/stdout.log
```

## 8. 安全边界

后端不会执行前端传来的任意 shell 命令。

允许的动作在 `backend/services/security.py`：

```text
model-info
check
quantize
benchmark
package
board-sync
board-run
board-deploy
deploy-qemu
matrix
matrix-report
pc-aipro-report
docker-build
```

后端使用 `subprocess.Popen([...], shell=False)`，并且对路径参数做工程目录限制。

## 9. 语法检查结果

我已经在生成包前执行：

```bash
python3 -m compileall backend
cd product-ui && tsc --noEmit --skipLibCheck
```

结果：Python 后端语法检查通过；TypeScript / TSX 类型语法检查通过。

## 10. 推荐接入顺序

1. 先启动后端，看 `/api/health` 是否正常。
2. 启动前端，看首页是否能显示模型和运行环境。
3. 先测试 `model-info`、`check` 这类安全短任务。
4. 再接 `benchmark`、`package`。
5. 最后接 `board-sync`、`board-run`、`deploy-qemu`。

这样可以避免一开始就被板端、CANN、QEMU 等重依赖卡住。
