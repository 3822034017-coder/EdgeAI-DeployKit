"use client";

import { useMemo, useState } from "react";
import { chatWithAssistant, type AssistantMessage } from "@/lib/api";
import type { ModelItem } from "@/lib/types";

type AssistantPanelProps = {
  selectedModel?: ModelItem;
};

function getModelName(model?: ModelItem) {
  if (!model) return "current_model";
  const value = model as ModelItem & { name?: string; path?: string };
  if (value.name) return value.name;
  if (value.path) {
    const parts = value.path.split("/").filter(Boolean);
    return parts[parts.length - 2] || parts[parts.length - 1] || "current_model";
  }
  return "current_model";
}

const quickPrompts = [
  "给出后端启动命令",
  "给出前端启动命令",
  "怎么生成当前模型报告",
  "我现在要部署 yolov5n_opset11 到香橙派，给出 package、board-sync、board-run 命令",
];

export function AssistantPanel({ selectedModel }: AssistantPanelProps) {
  const modelName = useMemo(() => getModelName(selectedModel), [selectedModel]);
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      role: "assistant",
      content:
        "你好，我是 EdgeAI-DeployKit 本地助手。可以帮你生成部署命令、分析板端日志、解释报告生成流程和排查 WebUI/后端问题。",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    const contextualContent = `当前 WebUI 选择模型：${modelName}\n用户问题：${content}`;
    const nextMessages: AssistantMessage[] = [
      ...messages,
      { role: "user", content: contextualContent },
    ];

    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const resp = await chatWithAssistant(nextMessages);
      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: resp.content || "助手没有返回内容。",
        },
      ]);
    } catch (err) {
      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: `助手请求失败：${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="workspace-panel-card workspace-panel-card-large">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <div className="text-xs uppercase tracking-[0.26em] text-cyan-200/70">
            Local DeepSeek Assistant
          </div>
          <h2 className="text-2xl font-semibold text-white">项目助手</h2>
          <p className="text-sm leading-6 text-slate-300/80">
            当前模型：<span className="font-medium text-cyan-100">{modelName}</span>。常用工程命令由后端模板直接返回，开放问题由本地 Ollama / DeepSeek-R1 处理。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => send(prompt)}
              disabled={loading}
              className="rounded-full border border-cyan-300/20 bg-cyan-300/8 px-3 py-1.5 text-xs text-cyan-50 transition hover:border-cyan-200/50 hover:bg-cyan-300/15 disabled:opacity-50"
            >
              {prompt.length > 20 ? `${prompt.slice(0, 20)}...` : prompt}
            </button>
          ))}
        </div>

        <div className="max-h-[420px] min-h-[260px] overflow-y-auto rounded-2xl border border-white/10 bg-black/25 p-4">
          <div className="flex flex-col gap-3">
            {messages.map((message, index) => {
              const isUser = message.role === "user";
              const text = isUser
                ? message.content.replace(/^当前 WebUI 选择模型：.*\n用户问题：/s, "")
                : message.content;

              return (
                <div
                  key={`${message.role}-${index}`}
                  className={
                    isUser
                      ? "ml-auto max-w-[88%] rounded-2xl border border-cyan-300/20 bg-cyan-400/12 px-4 py-3 text-sm leading-6 text-cyan-50"
                      : "mr-auto max-w-[92%] whitespace-pre-wrap rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3 text-sm leading-6 text-slate-100"
                  }
                >
                  {text}
                </div>
              );
            })}
            {loading ? (
              <div className="mr-auto rounded-2xl border border-cyan-300/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">
                本地助手正在生成回答...
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                event.preventDefault();
                send();
              }
            }}
            placeholder="例如：帮我分析 board-run 失败，或者给出 yolov5n_opset11 部署命令。Ctrl+Enter 发送。"
            className="min-h-[64px] flex-1 resize-none rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50"
          />
          <button
            type="button"
            onClick={() => send()}
            disabled={loading || !input.trim()}
            className="rounded-2xl border border-cyan-300/40 bg-cyan-300/12 px-5 py-3 text-sm font-semibold text-cyan-50 transition hover:border-cyan-200/70 hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:opacity-45"
          >
            发送
          </button>
        </div>
      </div>
    </section>
  );
}
