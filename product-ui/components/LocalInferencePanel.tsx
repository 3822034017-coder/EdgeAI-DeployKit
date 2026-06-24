"use client";

import * as React from "react";
import { createJob, runLocalInferenceFlow } from "@/lib/api";

type FlowResult = {
  ok?: boolean;
  message?: string;
  package_name?: string;
  package_dir?: string;
  input?: string | null;
  stages?: Array<{ stage?: string; ok?: boolean; code?: number; skipped?: boolean; output?: string }>;
  artifacts?: Record<string, boolean | string | null | undefined>;
  task_result?: unknown;
};

function packageDir(packageName?: string) {
  return `outputs/packages/${packageName || "<package>"}`;
}

function stageLabel(stage?: string) {
  const labels: Record<string, string> = {
    analyze: "Analyze",
    "task-init": "Task Init",
    "prepare-input": "Prepare Input",
    "local-run": "Local Run",
    "task-render": "Task Render",
    report: "Local Report",
  };
  return labels[stage || ""] || stage || "Stage";
}

function shortText(value: unknown, max = 2200) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}\n...` : text;
}

export function LocalInferencePanel({
  packageName,
  selectedInputPath,
  onUploadInput,
  onRefresh,
  onOpenRuntime,
  onOpenReports,
}: {
  packageName?: string;
  selectedInputPath?: string;
  onUploadInput?: (file: File) => void | Promise<void>;
  onRefresh?: () => void | Promise<void>;
  onOpenRuntime?: () => void;
  onOpenReports?: () => void;
}) {
  const [busy, setBusy] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [error, setError] = React.useState("");
  const [result, setResult] = React.useState<FlowResult | null>(null);

  const pkg = packageName || "";
  const validPackage = Boolean(pkg && pkg !== "model" && pkg !== "<package>");

  async function submit(action: "analyze" | "prepare-input" | "local-run" | "local-report") {
    if (!validPackage) {
      setError("请先完成模型上传 / 转换，生成可用的本地 package。");
      return;
    }
    if (action === "prepare-input" && !selectedInputPath) {
      setError("请先上传一张符合任务提示的测试输入图片。数字识别上传数字图片，分类上传实物图片，检测上传包含目标的图片。");
      return;
    }

    setBusy(action);
    setError("");
    setMessage("");
    try {
      const params: Record<string, string | number | boolean | null | undefined> = {
        package: packageDir(pkg),
      };
      if (action === "prepare-input") params.input = selectedInputPath;
      const job = await createJob({ action, params });
      setMessage(`已提交 ${action} 任务：${job.id}。请在 Runtime 查看输出和日志。`);
      onOpenRuntime?.();
      await onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  async function runOneClickFlow() {
    if (!validPackage) {
      setError("请先完成模型上传 / 转换，生成可用的本地 package。");
      return;
    }
    if (!selectedInputPath) {
      setError("请先上传测试输入。图像分类模型请上传一张实物图片，数字识别模型请上传单个数字图片。");
      return;
    }

    setBusy("one-click");
    setError("");
    setMessage("正在执行本地推理闭环：Analyze / Task Init → Prepare Input → Local Run → Task Render → Report ...");
    setResult(null);
    try {
      const next = await runLocalInferenceFlow({ package_name: pkg, input: selectedInputPath, force_report: true });
      setResult(next);
      if (next.ok) {
        setMessage("本地推理闭环已完成。结果和报告已生成，可以查看 Task Result 或打开 Reports。");
      } else {
        setError(next.message || "本地推理闭环失败，请查看阶段日志。");
      }
      await onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }

  const stages = result?.stages || [];
  const artifacts = result?.artifacts || {};

  return (
    <section className="rounded-[30px] border border-white/10 bg-slate-950/50 p-6 shadow-2xl shadow-black/25">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="product-kicker">Local inference</div>
          <h2 className="mt-2 text-2xl font-black text-white">本地推理流程</h2>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
            当前只显示本地流程：系统先读取模型任务配置，提示你上传测试输入，然后自动完成输入准备、本地 ONNX Runtime 推理、任务化结果渲染和报告生成。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={onOpenReports} className="rounded-xl border border-cyan-300/25 bg-cyan-300/10 px-4 py-2 text-xs font-bold text-cyan-100">
            打开报告
          </button>
          <button type="button" onClick={onOpenRuntime} className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-bold text-slate-200">
            查看 Runtime
          </button>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-cyan-300/15 bg-cyan-300/5 p-4 text-sm leading-6 text-slate-300">
        <div>当前 package：<span className="font-mono font-bold text-cyan-100">{packageName || "等待模型转换"}</span></div>
        <div>目录：<span className="font-mono text-slate-400">{packageDir(packageName)}</span></div>
        <div>当前输入：<span className="font-mono text-slate-400">{selectedInputPath || "尚未上传"}</span></div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <label className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
          <div className="text-xs font-black uppercase tracking-[0.25em] text-pink-100/75">Input</div>
          <div className="mt-2 font-bold text-white">上传任务测试输入</div>
          <p className="mt-2 text-xs leading-6 text-slate-400">
            根据上方任务向导选择输入：MNIST 上传数字图片，分类模型上传实物图片，YOLO 上传包含目标的图片。上传后再点击“一键本地推理”。
          </p>
          <input
            type="file"
            accept="image/*,.npy,.txt,.csv"
            className="mt-4 block w-full text-xs"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void onUploadInput?.(file);
            }}
          />
        </label>

        <div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/5 p-4">
          <div className="text-xs font-black uppercase tracking-[0.25em] text-cyan-100/80">One click flow</div>
          <h3 className="mt-2 text-lg font-black text-white">一键执行本地推理闭环</h3>
          <p className="mt-2 text-xs leading-6 text-slate-400">
            这一步会自动执行：Analyze / Task Init → Prepare Input → Local Run → Task Render → Local Report。适合用户上传模型和测试输入后直接跑完整流程。
          </p>
          <button
            type="button"
            onClick={() => void runOneClickFlow()}
            disabled={Boolean(busy) || !validPackage || !selectedInputPath}
            className="mt-4 rounded-2xl border border-cyan-300/30 bg-cyan-300/15 px-5 py-3 text-sm font-black text-cyan-100 transition hover:border-cyan-300/60 hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:opacity-45"
          >
            {busy === "one-click" ? "正在执行完整本地推理..." : "开始本地推理并生成报告"}
          </button>
          {!selectedInputPath ? <div className="mt-3 text-xs text-amber-100/80">请先上传测试输入，按钮才会解锁。</div> : null}
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["analyze", "Analyze", "重新读取输入输出签名、算子结构和任务识别依据。"],
          ["prepare-input", "Prepare Input", "只把当前测试输入转换成 input.npy。"],
          ["local-run", "Local Run", "只在本机 ONNX Runtime CPU 上执行推理。"],
          ["local-report", "Local Report", "只生成 report.md / report.pdf。"],
        ].map(([action, title, desc]) => (
          <button
            key={action}
            type="button"
            onClick={() => void submit(action as "analyze" | "prepare-input" | "local-run" | "local-report")}
            className="rounded-2xl border border-white/10 bg-black/20 p-4 text-left transition hover:border-cyan-300/30 hover:bg-cyan-300/10"
            disabled={Boolean(busy)}
          >
            <div className="text-sm font-black text-white">{busy === action ? "运行中..." : title}</div>
            <p className="mt-2 text-xs leading-6 text-slate-400">{desc}</p>
          </button>
        ))}
      </div>

      {message ? <div className="mt-4 rounded-xl border border-cyan-300/20 bg-cyan-300/10 p-3 text-xs text-cyan-100">{message}</div> : null}
      {error ? <div className="mt-4 rounded-xl border border-rose-300/20 bg-rose-500/10 p-3 text-xs text-rose-100">{error}</div> : null}

      {stages.length ? (
        <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="text-xs font-black uppercase tracking-[0.25em] text-slate-400">Stage result</div>
          <div className="mt-3 grid gap-2 md:grid-cols-2 lg:grid-cols-3">
            {stages.map((stage, index) => (
              <div key={`${stage.stage || "stage"}-${index}`} className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-black text-white">{stageLabel(stage.stage)}</span>
                  <span className={stage.skipped ? "text-xs text-slate-400" : stage.ok ? "text-xs text-emerald-200" : "text-xs text-rose-200"}>
                    {stage.skipped ? "skipped" : stage.ok ? "ok" : `failed ${stage.code ?? ""}`}
                  </span>
                </div>
                {stage.output ? <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap rounded-lg bg-black/30 p-2 text-[10px] leading-4 text-slate-400">{shortText(stage.output, 800)}</pre> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {Object.keys(artifacts).length ? (
        <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4 text-xs text-slate-300">
          <div className="mb-2 font-black uppercase tracking-[0.25em] text-slate-400">Artifacts</div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(artifacts).map(([name, value]) => (
              <div key={name} className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2">
                <span className="font-mono text-slate-400">{name}</span>：<span className={value ? "text-emerald-200" : "text-rose-200"}>{String(Boolean(value))}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {result?.task_result ? (
        <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="text-xs font-black uppercase tracking-[0.25em] text-slate-400">Task result preview</div>
          <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950/70 p-4 text-xs leading-5 text-slate-300">{shortText(result.task_result, 6000)}</pre>
        </div>
      ) : null}
    </section>
  );
}
