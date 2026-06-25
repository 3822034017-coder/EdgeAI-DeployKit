from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def is_llm_package(package_dir: str | Path) -> bool:
    package = Path(package_dir)
    task = _read_json(package / "model_task.json", {}) or {}
    return bool((package / "model.gguf").exists() or (package / "llm_runtime.json").exists() or task.get("task_type") == "llm_chat")


def _model_path(package_dir: Path) -> Path:
    cfg = _read_json(package_dir / "llm_runtime.json", {}) or {}
    raw = cfg.get("model_path") or "model.gguf"
    path = Path(str(raw))
    return path if path.is_absolute() else package_dir / path


def _prompt_from_package(package_dir: Path, prompt: str | None = None) -> str:
    if prompt and str(prompt).strip():
        return str(prompt).strip()
    for name in ("input.txt", "prompt.txt"):
        path = package_dir / name
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                return text
    raise ValueError("LLM run requires a prompt string or package/input.txt")


def _infer_chat_profile(model_path: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    original_name = str(cfg.get("original_model_name") or "")
    name = f"{original_name} {model_path.name} {cfg.get('model_family') or ''} {cfg.get('chat_template') or ''}".lower()
    is_chat_like = any(
        token in name
        for token in (
            "instruct",
            "chat",
            "assistant",
            "qwen",
            "deepseek",
            "phi",
            "gemma",
            "zephyr",
            "openchat",
            "llama",
            "mistral",
            "vicuna",
            "smollm",
        )
    )
    template = str(cfg.get("chat_template") or "").strip().lower()
    if not template:
        if "qwen" in name:
            template = "chatml"
        elif "deepseek" in name:
            template = "deepseek"
        elif "llama-3" in name or "llama3" in name:
            template = "llama3"
        elif "llama-2" in name or "llama2" in name:
            template = "llama2"
        elif "zephyr" in name:
            template = "zephyr"
        elif "openchat" in name:
            template = "openchat"
        elif "vicuna" in name:
            template = "vicuna"
        elif "phi4" in name:
            template = "phi4"
        elif "phi" in name:
            template = "phi3"
        elif "gemma" in name:
            template = "gemma"

    return {
        "mode": "chat" if is_chat_like else "completion",
        "chat_template": template or None,
        "system_prompt": str(
            cfg.get("system_prompt")
            or "You are a helpful local AI assistant. Answer the user's latest message directly and concisely."
        ),
        "quality_note": None
        if is_chat_like
        else (
            "This GGUF looks like a base/completion model, not an instruct/chat model. "
            "It can be deployed, but answers may be off-topic. Use an Instruct/Chat GGUF for reliable conversation."
        ),
    }


def _completion_prompt(prompt: str) -> str:
    text = prompt.strip()
    if not text or "Question:" in text or "Answer:" in text or "User:" in text or "Assistant:" in text:
        return text
    return f"Answer the following user message directly and briefly.\n\nUser message: {text}\n\nAnswer:"


def _run_with_llama_cpp_python(
    model_path: Path,
    prompt: str,
    max_tokens: int,
    temperature: float,
    profile: dict[str, Any],
) -> tuple[str, str] | None:
    try:
        from llama_cpp import Llama  # type: ignore
    except Exception:
        return None

    runtime_prompt = prompt if profile.get("mode") == "chat" else _completion_prompt(prompt)
    llm = Llama(model_path=str(model_path), n_ctx=2048, verbose=False)
    out = llm(runtime_prompt, max_tokens=max_tokens, temperature=temperature, stop=["User:", "\nUser message:"])
    text = ""
    try:
        choices = out.get("choices") or []
        if choices:
            text = str(choices[0].get("text") or "")
    except Exception:
        text = str(out)
    return text.strip(), "llama-cpp-python"


def _run_with_llama_cli(
    model_path: Path,
    prompt: str,
    max_tokens: int,
    temperature: float,
    profile: dict[str, Any],
) -> tuple[str, str] | None:
    exe = os.environ.get("EDGEAI_LLAMA_CLI") or shutil.which("llama-cli") or shutil.which("llama")
    if not exe:
        return None

    runtime_prompt = prompt if profile.get("mode") == "chat" else _completion_prompt(prompt)
    cmd = [
        exe,
        "-m",
        str(model_path),
        "-p",
        runtime_prompt,
        "-n",
        str(max_tokens),
        "--temp",
        str(temperature),
        "--single-turn",
        "--simple-io",
        "--no-display-prompt",
    ]
    if profile.get("system_prompt"):
        cmd.extend(["-sys", str(profile["system_prompt"])])
    if profile.get("chat_template"):
        cmd.extend(["--chat-template", str(profile["chat_template"])])

    proc = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout[-4000:])
    return _clean_llama_cli_output(proc.stdout or "", runtime_prompt), "llama-cli"


def _looks_like_llama_progress(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.count("\ufffd") >= 3:
        return True
    if len(stripped) >= 8:
        block_chars = sum(1 for ch in stripped if ord(ch) in (0x2580, 0x2584, 0x2588, 0x2590, 0x2591, 0x2592, 0x2593))
        if block_chars >= max(4, len(stripped) // 3):
            return True
    return False


def _clean_llama_cli_output(output: str, prompt: str) -> str:
    text = output.replace("\r\n", "\n").strip()
    marker = f"> {prompt}"
    idx = text.rfind(marker)
    if idx >= 0:
        text = text[idx + len(marker):]

    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines:
                lines.append("")
            continue
        if stripped.startswith("[ Prompt:") or stripped == "Exiting...":
            break
        if stripped.startswith(">"):
            continue
        if stripped.startswith(("Loading model", "build      :", "model      :", "modalities :")):
            continue
        if stripped.startswith(("available commands:", "/exit", "/regen", "/clear", "/read", "/glob")):
            continue
        if _looks_like_llama_progress(stripped):
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    return cleaned or text


def run_llm_package(
    package_dir: str | Path,
    prompt: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Dict[str, Any]:
    package = Path(package_dir)
    cfg = _read_json(package / "llm_runtime.json", {}) or {}
    model = _model_path(package)
    if not model.exists() or not model.is_file():
        raise FileNotFoundError(f"LLM model file not found: {model}")

    prompt_text = _prompt_from_package(package, prompt)
    max_tokens = int(max_tokens or cfg.get("default_max_tokens") or 256)
    temperature = float(temperature if temperature is not None else cfg.get("default_temperature", 0.7))
    profile = _infer_chat_profile(model, cfg)

    started = time.perf_counter()
    generated = _run_with_llama_cpp_python(model, prompt_text, max_tokens, temperature, profile)
    if generated is None:
        generated = _run_with_llama_cli(model, prompt_text, max_tokens, temperature, profile)
    if generated is None:
        raise RuntimeError(
            "No local LLM runtime found. Install llama-cpp-python, or install llama.cpp and set EDGEAI_LLAMA_CLI."
        )

    response, provider = generated
    elapsed = (time.perf_counter() - started) * 1000.0

    result: Dict[str, Any] = {
        "success": True,
        "backend": "llm",
        "provider": provider,
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
        },
        "package_dir": str(package),
        "model": str(model),
        "input": {"name": "prompt", "text": prompt_text},
        "outputs": [{"name": "response", "text": response}],
        "response": response,
        "latency_ms": round(float(elapsed), 4),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "chat_profile": profile,
    }
    _write_json(package / "local_result.json", result)
    (package / "local_output.txt").write_text(response + "\n", encoding="utf-8")
    return result
