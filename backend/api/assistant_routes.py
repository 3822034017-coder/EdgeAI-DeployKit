from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import List, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]


def load_env_file() -> None:
    """Load .env without adding python-dotenv dependency."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str


class AssistantChatRequest(BaseModel):
    messages: List[AssistantMessage]


SYSTEM_PROMPT = """你是 EdgeAI-DeployKit 项目的本地 DeepSeek 助手。
你必须直接回答用户问题，回答要简洁、工程化、以可执行命令为主。

项目事实：
- 项目根目录：/root/edge-ai-deploy-kit
- 后端：backend/，FastAPI，端口 8001
- 前端：product-ui/，Next.js，端口 3000
- 核心 CLI：edgeai
- 板端：香橙派 AIPro
- 板端 IP：192.168.0.36
- 板端用户：HwHiAiUser
- 常用推理端口：7891
- 当前模型包目录：outputs/packages/<model_name>/
- 报告目录：reports/
- 当前模型报告应使用：edgeai report --model <current_model>，再执行 edgeai pdf

常用正确命令示例：

后端启动：
cd /root/edge-ai-deploy-kit
mkdir -p outputs/logs
fuser -k 8001/tcp 2>/dev/null || true
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 > outputs/logs/product-api.log 2>&1 &

前端启动：
cd /root/edge-ai-deploy-kit/product-ui
pnpm run typecheck && rm -rf .next && pnpm build
fuser -k 3000/tcp 2>/dev/null || true
pnpm exec next start -H 0.0.0.0 -p 3000

yolov5n_opset11 部署：
cd /root/edge-ai-deploy-kit
source .venv/bin/activate
edgeai package --model models/zoo/yolov5n_opset11/model.onnx --type yolov5n --input /root/edge-ai-deploy-kit/photo/car.png
edgeai board-sync --host 192.168.0.36 --user HwHiAiUser --package outputs/packages/yolov5n_opset11 --model-name yolov5n_opset11
edgeai board-run --host 192.168.0.36 --user HwHiAiUser --package outputs/packages/yolov5n_opset11 --model-name yolov5n_opset11 --port 7891 --wait 8

重要限制：
- 不要编造 package add、config board-sync、config board-run 这类不存在命令。
- 如果不确定，说明需要用户提供日志或文件，不要硬猜。
- 对部署命令，优先给完整 bash 命令。
"""


def _ollama_base_url() -> str:
    base = os.getenv("OLLAMA_BASE_URL", "").strip().rstrip("/")
    if not base:
        base = os.getenv("DEEPSEEK_BASE_URL", "http://127.0.0.1:11434/v1").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base or "http://127.0.0.1:11434"


def call_deepseek(messages: List[AssistantMessage]) -> str:
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-r1:1.5b")
    base = _ollama_base_url()

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *[m.model_dump() for m in messages[-20:]],
        ],
        "options": {
            "temperature": float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
            "num_ctx": int(os.getenv("DEEPSEEK_NUM_CTX", "4096")),
        },
    }

    req = urllib.request.Request(
        f"{base}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "240"))) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data.get("message", {}).get("content", "")


@router.get("/assistant/health")
def assistant_health():
    return {
        "ok": True,
        "provider": "ollama-deepseek-only",
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-r1:1.5b"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "http://127.0.0.1:11434/v1"),
        "template_mode": False,
    }


@router.post("/assistant/chat")
def assistant_chat(payload: AssistantChatRequest):
    try:
        content = call_deepseek(payload.messages)
        return {
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-r1:1.5b"),
            "provider": "ollama-deepseek-only",
            "content": content,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DeepSeek/Ollama request failed: {exc}")
