"use client";

import React from "react";
import { API_BASE } from "@/lib/api";

const { useEffect, useState } = React;

type TaskConfig = {
  package_name?: string;
  task_type?: string;
  task_title?: string;
  inferred_task_type?: string;
  inference_reasons?: string[];
  input?: {
    type?: string;
    prompt?: string;
    name?: string;
    shape?: Array<string | number>;
    dtype?: string;
    layout?: string;
  };
  output?: {
    type?: string;
    name?: string;
    shape?: Array<string | number>;
    dtype?: string;
    class_count?: number;
    label_map?: string;
    label_language?: string;
  };
  ui?: {
    input_prompt?: string;
    recommended_examples?: string[];
    result_view?: string;
  };
  operator_summary?: {
    node_count?: number;
    operator_count?: Record<string, number>;
  };
};

type TaskResponse = TaskConfig & {
  ok?: boolean;
  package_dir?: string;
  task_file?: string;
  error?: string;
};

const ACTIVE_RUN_KEY = "edgeai.currentRun";
const ACTIVE_LOCAL_KEYS = [
  "edgeai.activeLocalSession",
  "edgeai.activeLocalRunSession",
  "edgeai.localRun.session",
  "edgeai.localRunSession",
  "edgeai.active.local.session",
];

function cleanName(value: unknown) {
  const parts = String(value || "")
    .trim()
    .replace(/\\/g, "/")
    .split("/")
    .filter(Boolean);
  const raw = parts.pop() || "";
  const parent = parts.pop() || "";
  const stem = raw.replace(/\.(onnx|pt|pth|ckpt|h5|hdf5|keras|pb|tflite|pkl|joblib|sav|bst|xgb|lgb|gguf|txt|json|zip)$/i, "");
  const base = stem === "model" || stem.startsWith("model_") ? parent : stem;
  return base.replace(/[^a-zA-Z0-9_.-]+/g, "_").replace(/^_+|_+$/g, "") || "";
}

function safeJson(value: string | null) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function extractPackageName(value: unknown): string {
  if (!value) return "";
  if (typeof value === "string") return cleanName(value);
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = extractPackageName(item);
      if (found) return found;
    }
    return "";
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const direct = obj.packageName || obj.package_name || obj.package || obj.model_name || obj.modelName || obj.name;
    const directClean = cleanName(direct);
    if (directClean) return directClean;

    const pathLike = obj.packageDir || obj.package_dir || obj.outputDir || obj.output_dir || obj.modelPath || obj.model_path;
    const pathClean = cleanName(pathLike);
    if (pathClean) return pathClean;

    for (const item of Object.values(obj)) {
      const found = extractPackageName(item);
      if (found) return found;
    }
  }
  return "";
}

function readActiveLocalPackage() {
  if (typeof window === "undefined") return "";

  const preferred = safeJson(window.localStorage.getItem(ACTIVE_RUN_KEY));
  if (preferred && typeof preferred === "object") {
    const found = extractPackageName((preferred as Record<string, unknown>).packageName);
    if (found) return found;
  }

  for (const key of ACTIVE_LOCAL_KEYS) {
    const found = extractPackageName(safeJson(window.localStorage.getItem(key)) || window.localStorage.getItem(key));
    if (found) return found;
  }

  try {
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const key = window.localStorage.key(i) || "";
      const lower = key.toLowerCase();
      if (!lower.includes("edgeai") && !lower.includes("local")) continue;
      if (!lower.includes("session") && !lower.includes("run")) continue;
      const found = extractPackageName(safeJson(window.localStorage.getItem(key)) || window.localStorage.getItem(key));
      if (found) return found;
    }
  } catch {
    // ignore
  }

  return "";
}

function formatShape(shape?: Array<string | number>) {
  if (!shape || !shape.length) return "unknown";
  return `[${shape.map((x) => String(x)).join(", ")}]`;
}

function taskBadge(taskType?: string) {
  const type = String(taskType || "unknown");
  if (type === "image_classification") return "图像分类";
  if (type === "digit_classification") return "数字识别";
  if (type === "object_detection") return "目标检测";
  if (type === "segmentation") return "图像分割";
  if (type === "text_classification") return "文本分类";
  if (type === "llm_chat") return "本地大模型对话";
  return type;
}

function taskPromptFallback(taskType?: string) {
  if (taskType === "digit_classification") return "请上传一张单个手写数字图片，系统会输出识别数字和置信度。";
  if (taskType === "object_detection") return "请上传一张包含目标物体的图片，系统会输出带检测框的结果图。";
  if (taskType === "segmentation") return "请上传待分割图片，系统会输出 mask 和叠加可视化结果。";
  if (taskType === "text_classification") return "请输入一段待分类文本，系统会输出分类标签和置信度。";
  if (taskType === "llm_chat") return "请输入对话内容，系统会使用本地大模型生成回复。";
  return "请上传一张实物图片，例如猫、狗、汽车、杯子等，系统会输出 TopK 分类结果。";
}

export function TaskGuidancePanel({ packageName, compact = false }: { packageName?: string; compact?: boolean }) {
  const [task, setTask] = useState(null as TaskResponse | null);
  const [loading, setLoading] = useState(false as boolean);
  const [error, setError] = useState("" as string);
  const [resolvedPackage, setResolvedPackage] = useState(cleanName(packageName) as string);

  async function loadTaskConfig() {
    const nextPackage = cleanName(packageName) || readActiveLocalPackage();
    setResolvedPackage(nextPackage);

    if (!nextPackage || nextPackage === "model") {
      setTask(null);
      setError("当前还没有可用的本地模型 package。请先完成 Convert / Analyze，或生成 model_task.json。");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const q = new URLSearchParams({ package_name: nextPackage, auto_create: "true", t: String(Date.now()) });
      const res = await fetch(`${API_BASE}/api/local-task-config?${q.toString()}`, { cache: "no-store" });
      if (!res.ok) throw new Error(await res.text());
      setTask((await res.json()) as TaskResponse);
    } catch (err) {
      setTask(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTaskConfig();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [packageName]);

  const taskType = task?.task_type || task?.inferred_task_type;
  const prompt = task?.ui?.input_prompt || task?.input?.prompt || taskPromptFallback(taskType);
  const examples = task?.ui?.recommended_examples || [];
  const ops = task?.operator_summary?.operator_count || {};
  const topOps = Object.entries(ops).slice(0, compact ? 4 : 8);

  return (
    <div className="workspace-panel-card workspace-panel-card-large">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="workspace-panel-kicker">Local Task System</div>
            <h2 className="text-lg font-semibold text-white">本地推理任务向导</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
              系统会读取 <code>model_task.json</code>，根据模型任务类型提示用户应该上传什么输入，并决定后续结果展示方式。
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadTaskConfig()}
            className="rounded-xl border border-cyan/30 bg-cyan/10 px-3 py-2 text-xs text-cyan transition hover:bg-cyan/20"
          >
            刷新任务信息
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Package</div>
            <div className="mt-2 break-all text-sm font-semibold text-slate-100">{resolvedPackage || "未选择"}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Task Type</div>
            <div className="mt-2 text-sm font-semibold text-emerald-200">{task ? taskBadge(taskType) : "未生成"}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Result View</div>
            <div className="mt-2 text-sm font-semibold text-slate-100">{task?.ui?.result_view || task?.output?.type || "等待任务配置"}</div>
          </div>
        </div>

        {task ? (
          <div className="rounded-2xl border border-cyan/20 bg-cyan/5 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-cyan">Input Guidance</div>
            <div className="mt-2 text-base font-semibold text-white">{prompt}</div>
            <div className="mt-3 grid gap-3 text-sm text-slate-300 md:grid-cols-2">
              <div>
                输入：{task.input?.name || "input"} / {task.input?.type || "unknown"} / {formatShape(task.input?.shape)} / {task.input?.layout || "layout unknown"}
              </div>
              <div>
                输出：{task.output?.name || "output"} / {task.output?.type || "unknown"} / {formatShape(task.output?.shape)}
              </div>
            </div>
            {examples.length ? (
              <div className="mt-3 text-xs text-slate-400">推荐测试样例：{examples.join("，")}</div>
            ) : null}
          </div>
        ) : (
          <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm leading-6 text-amber-100">
            {loading ? "正在读取任务配置..." : "还没有读取到 model_task.json。若刚提交模型，请等待自动初始化任务完成；系统会在 Convert → Analyze 后自动生成任务配置。"}
            {error ? <div className="mt-2 break-all text-xs text-amber-200/80">{error}</div> : null}
          </div>
        )}

        {!compact && task?.inference_reasons?.length ? (
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
            <div className="mb-2 text-xs uppercase tracking-[0.18em] text-slate-500">Inference Reasons</div>
            {task.inference_reasons.map((item: string) => <div key={item}>- {item}</div>)}
          </div>
        ) : null}

        {!compact && topOps.length ? (
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
            <div className="mb-2 text-xs uppercase tracking-[0.18em] text-slate-500">Operator Summary</div>
            <div className="flex flex-wrap gap-2">
              {topOps.map(([name, count]) => (
                <span key={name} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs">
                  {name}: {String(count)}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
