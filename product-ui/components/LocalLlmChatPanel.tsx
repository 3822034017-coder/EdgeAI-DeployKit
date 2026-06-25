"use client";

import * as React from "react";
import { runLocalInferenceFlow } from "@/lib/api";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type LocalLlmChatPanelProps = {
  packageName?: string;
  onRefresh?: () => void | Promise<void>;
  onOpenReports?: () => void;
};

function lastMessage(messages: ChatMessage[], role: ChatMessage["role"]) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === role) return messages[index].content.trim();
  }
  return "";
}

function looksLikeCreativeRequest(text: string) {
  return /写|创作|生成|小说|故事|作文|文章|报告|总结|介绍|列出|解释/.test(text);
}

function looksLikeSupplement(text: string) {
  return text.length <= 80 && /主题|题目|就是|关于|围绕|背景|主角|风格|字数|改成|用中文|用英文/.test(text);
}

function asksForMoreDetails(text: string) {
  return /告诉我|请提供|请说明|主题|情节|细节|具体|更多/.test(text);
}

function requestedTokenBudget(text: string, current: number) {
  const match = text.match(/(\d{2,5})\s*(字|个字|汉字|words?|tokens?)/i);
  if (!match) return current;
  const amount = Number(match[1] || 0);
  if (!Number.isFinite(amount) || amount <= 0) return current;
  const multiplier = /words?|tokens?/i.test(match[2] || "") ? 1.4 : 1.6;
  return Math.min(4096, Math.max(current, Math.ceil(amount * multiplier)));
}

function buildPrompt(messages: ChatMessage[], nextUserMessage: string) {
  const current = nextUserMessage.trim();
  if (messages.length === 0) return current;

  const previousUser = lastMessage(messages, "user");
  const previousAssistant = lastMessage(messages, "assistant");
  const isCompletingPreviousTask =
    looksLikeSupplement(current) &&
    looksLikeCreativeRequest(previousUser) &&
    asksForMoreDetails(previousAssistant);

  if (!isCompletingPreviousTask) return current;

  return [
    "你正在继续完成上一轮未完成的任务。",
    `上一轮用户请求：${previousUser}`,
    `上一轮助手追问：${previousAssistant}`,
    `用户现在补充：${current}`,
    "请现在直接完成上一轮用户请求，不要继续追问，不要复述以上对话。",
    "请遵守用户要求的语言、体裁和字数。",
  ].join("\n");
}

function buildRetryPrompt(messages: ChatMessage[], nextUserMessage: string) {
  const current = nextUserMessage.trim();
  const previousUser = lastMessage(messages, "user");
  const previousAssistant = lastMessage(messages, "assistant");
  if (looksLikeSupplement(current) && looksLikeCreativeRequest(previousUser)) {
    return [
      "请直接完成任务，不要复述问题，不要继续询问。",
      `任务：${previousUser}`,
      `补充信息：${current}`,
      previousAssistant ? `上一轮助手曾说：${previousAssistant}` : "",
      "现在给出最终内容。",
    ].filter(Boolean).join("\n");
  }
  return `请直接回答下面的问题，不要复述问题本身，不要只重复用户原话。\n\n用户问题：${current}\n\n回答：`;
}

function normalizeText(value: string) {
  return value.replace(/\s+/g, "").replace(/[，。！？、,.!?:：；;'"“”‘’`]/g, "").toLowerCase();
}

function looksLikeWeakResponse(response: string, current: string, messages: ChatMessage[]) {
  const cleanResponse = normalizeText(response);
  const cleanCurrent = normalizeText(current);
  if (!cleanResponse) return true;
  if (cleanResponse === cleanCurrent) return true;
  if (cleanCurrent && cleanResponse.includes(cleanCurrent) && cleanResponse.length <= cleanCurrent.length + 8) return true;
  if (/请告诉我|请提供|主题或情节|主题|情节细节/.test(response) && looksLikeSupplement(current) && looksLikeCreativeRequest(lastMessage(messages, "user"))) return true;
  return false;
}

function extractResponse(payload: unknown) {
  const data = payload as {
    task_result?: { conversation?: { response?: string }; summary?: { primary?: string } };
    stages?: Array<{ stage?: string; output?: string }>;
  };
  const direct = data.task_result?.conversation?.response;
  if (direct && direct.trim()) return direct.trim();
  const primary = data.task_result?.summary?.primary;
  if (primary && primary.trim() && primary !== "Chat output generated.") return primary.trim();
  const runStage = data.stages?.find((stage) => stage.stage === "local-run");
  if (!runStage?.output) return "";
  try {
    const parsed = JSON.parse(runStage.output);
    return String(parsed.response || parsed.outputs?.[0]?.text || "").trim();
  } catch {
    return runStage.output.trim();
  }
}

export function LocalLlmChatPanel({ packageName, onRefresh, onOpenReports }: LocalLlmChatPanelProps) {
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [input, setInput] = React.useState("Hello, introduce yourself briefly.");
  const [maxTokens, setMaxTokens] = React.useState(512);
  const [temperature, setTemperature] = React.useState(0.2);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");

  const validPackage = Boolean(packageName && packageName !== "model" && packageName !== "<package>");
  const genericPackage = ["model_local", "model", "user_model_local", "user_model"].includes(packageName || "");

  async function sendMessage() {
    const text = input.trim();
    if (!text || !validPackage || busy) return;
    const prompt = buildPrompt(messages, text);
    const optimistic = [...messages, { role: "user" as const, content: text }];
    setMessages(optimistic);
    setInput("");
    setError("");
    setBusy(true);
    try {
      const effectiveMaxTokens = requestedTokenBudget(text, maxTokens);
      let result = await runLocalInferenceFlow({
        package_name: packageName || "",
        prompt,
        max_tokens: effectiveMaxTokens,
        temperature,
        force_report: true,
      });
      let response = extractResponse(result) || "The local model did not generate text for this prompt.";
      if (looksLikeWeakResponse(response, text, messages)) {
        result = await runLocalInferenceFlow({
          package_name: packageName || "",
          prompt: buildRetryPrompt(messages, text),
          max_tokens: effectiveMaxTokens,
          temperature: Math.max(temperature, 0.5),
          force_report: true,
        });
        response = extractResponse(result) || response;
      }
      setMessages([...optimistic, { role: "assistant", content: response }]);
      await onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setMessages(messages);
      setInput(text);
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(event: any) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  }

  return (
    <section className="rounded-[30px] border border-emerald-300/20 bg-slate-950/55 p-6 shadow-2xl shadow-black/25">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-black uppercase tracking-[0.25em] text-emerald-100/80">Local GGUF Chat</div>
          <h2 className="mt-2 text-2xl font-black text-white">本地大语言模型对话</h2>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
            当前 package 会作为本地 GGUF 部署运行，消息直接发送到本机 llama.cpp runtime，不调用云端模型。
          </p>
          <p className="mt-2 max-w-3xl text-xs leading-6 text-amber-100/85">
            对话质量取决于模型本身。建议上传文件名包含 Instruct / Chat 的 GGUF，例如 Qwen、Phi、Gemma、DeepSeek、Zephyr 等指令模型；基础续写模型可以部署，但可能答非所问。
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-xs text-slate-300">
          <div className="text-slate-500">Package</div>
          <div className="mt-1 font-mono font-bold text-emerald-100">{packageName || "waiting"}</div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_220px]">
        {genericPackage ? (
          <div className="lg:col-span-2 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-xs leading-6 text-amber-100">
            当前 package 名是通用的 {packageName}，很可能来自 model.gguf 或 user_model 这类无法识别家族的基础模型。基础续写模型可以部署，但经常会复读、追问或答非所问；如果要稳定聊天和长文生成，建议上传 Instruct / Chat GGUF，例如 Qwen、Phi、Gemma、DeepSeek、Zephyr、SmolLM 等模型。
          </div>
        ) : null}
        <div className="min-h-[320px] rounded-2xl border border-white/10 bg-black/25 p-4">
          <div className="flex h-[300px] flex-col gap-3 overflow-auto pr-1">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-500">
                等待第一条对话
              </div>
            ) : (
              messages.map((message, index) => {
                const isUser = message.role === "user";
                return (
                  <div key={`${message.role}-${index}`} className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                    {!isUser ? <div className="mt-1 h-6 w-6 shrink-0 rounded-full border border-emerald-300/25 bg-emerald-300/10 text-center text-[10px] font-black leading-6 text-emerald-100">AI</div> : null}
                    <div className={`max-w-[82%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${isUser ? "bg-cyan-300/15 text-cyan-50" : "bg-white/[0.06] text-slate-100"}`}>
                      {message.content}
                    </div>
                    {isUser ? <div className="mt-1 h-6 w-6 shrink-0 rounded-full border border-cyan-300/25 bg-cyan-300/10 text-center text-[10px] font-black leading-6 text-cyan-100">ME</div> : null}
                  </div>
                );
              })
            )}
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!validPackage || busy}
              className="min-h-[88px] resize-none rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm leading-6 text-white outline-none transition focus:border-emerald-300/40 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => void sendMessage()}
              disabled={!validPackage || busy || !input.trim()}
              className="flex min-h-[88px] items-center justify-center gap-2 rounded-2xl border border-emerald-300/30 bg-emerald-300/15 px-5 text-sm font-black text-emerald-100 transition hover:bg-emerald-300/20 disabled:cursor-not-allowed disabled:opacity-45"
            >
              {busy ? "Running..." : "Send"}
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <label className="block text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
            Max tokens
            <input
              type="number"
              min={16}
              max={4096}
              value={maxTokens}
              onChange={(event) => setMaxTokens(Number(event.target.value || 128))}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2 font-mono text-sm text-white"
            />
          </label>
          <label className="mt-4 block text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
            Temperature
            <input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(event) => setTemperature(Number(event.target.value || 0.7))}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2 font-mono text-sm text-white"
            />
          </label>
          <button
            type="button"
            onClick={() => setMessages([])}
            className="mt-4 w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-bold text-slate-200 hover:bg-white/[0.08]"
          >
            Clear chat
          </button>
          <button
            type="button"
            onClick={onOpenReports}
            className="mt-2 w-full rounded-xl border border-cyan-300/25 bg-cyan-300/10 px-3 py-2 text-xs font-bold text-cyan-100 hover:bg-cyan-300/20"
          >
            Open report
          </button>
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded-xl border border-rose-300/20 bg-rose-500/10 p-3 text-xs leading-6 text-rose-100">
          {error}
        </div>
      ) : null}
    </section>
  );
}
