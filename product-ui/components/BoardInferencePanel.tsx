"use client";

import type { ModelItem } from "@/lib/types";

export type BoardAction = "package" | "board-sync" | "board-run" | "board-deploy" | "report" | "html" | "pdf";

export function BoardInferencePanel({
  selectedModel,
  boardHost,
  onBoardHostChange,
  onRunAction,
  onOpenRuntime,
  onOpenReports,
}: {
  selectedModel?: ModelItem;
  boardHost: string;
  onBoardHostChange: (value: string) => void;
  onRunAction: (action: BoardAction) => void | Promise<void>;
  onOpenRuntime?: () => void;
  onOpenReports?: () => void;
}) {
  const modelLabel = selectedModel?.name || selectedModel?.path || "未选择模型";

  return (
    <section className="rounded-[30px] border border-white/10 bg-slate-950/50 p-6 shadow-2xl shadow-black/25">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="product-kicker">Optional board flow</div>
          <h2 className="mt-2 text-2xl font-black text-white">香橙派推理流程</h2>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
            该流程只在用户选择香橙派推理时显示。它不再占据本地推理主流程，用于板端打包、同步、运行和报告。
          </p>
        </div>
        <button type="button" onClick={onOpenRuntime} className="rounded-xl border border-white/10 bg-black/30 px-4 py-2 text-xs font-bold text-slate-200">
          查看日志
        </button>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Model</div>
          <div className="mt-2 break-all text-sm font-bold text-white">{modelLabel}</div>
        </div>
        <label className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
          <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Board host</div>
          <input
            value={boardHost}
            onChange={(event) => onBoardHostChange(event.target.value)}
            className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 font-mono text-xs text-white"
            placeholder="192.168.0.36"
          />
        </label>
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
          <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Result</div>
          <div className="mt-2">板端结果会写入 reports/edgeai_report.md/pdf。</div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["package", "Package", "生成可同步到板端的部署包。"],
          ["board-sync", "Board Sync", "同步 package 到香橙派。"],
          ["board-run", "Board Run", "在香橙派执行推理。"],
          ["report", "Board Report", "生成或刷新板端报告。"],
        ].map(([action, title, desc]) => (
          <button
            key={action}
            type="button"
            onClick={() => void onRunAction(action as BoardAction)}
            className="rounded-2xl border border-white/10 bg-black/20 p-4 text-left transition hover:border-pink-200/35 hover:bg-pink-200/10"
          >
            <div className="text-sm font-black text-white">{title}</div>
            <p className="mt-2 text-xs leading-6 text-slate-400">{desc}</p>
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={onOpenReports} className="rounded-xl border border-cyan-300/25 bg-cyan-300/10 px-4 py-2 text-xs font-bold text-cyan-100">
          打开 Reports
        </button>
      </div>
    </section>
  );
}
