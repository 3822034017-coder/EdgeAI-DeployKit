"use client";

import type { WorkspacePanel } from "./AppShell";
import type { DeployMode } from "./DeployModeDialog";

const localSteps = ["上传 / 转换模型", "识别任务类型", "上传测试输入", "本地推理", "结果与报告"];
const boardSteps = ["导入模型", "生成部署包", "同步到香橙派", "板端运行", "板端报告"];

export function ProductOverviewV1({
  selectedPackage,
  deployMode,
  onSelectPanel,
  onSelectDeployMode,
}: {
  selectedPackage?: string;
  deployMode: DeployMode | null;
  onSelectPanel: (panel: WorkspacePanel) => void;
  onSelectDeployMode: (mode: DeployMode) => void;
}) {
  return (
    <section className="overview-command-center">
      <div className="overview-command-head">
        <div>
          <div className="overview-kicker">Product Workspace</div>
          <h2>本地模型部署工作台</h2>
          <p>
            当前项目主线是跨平台本地推理工具包。Overview 不再只展示香橙派流程，而是把本地推理与香橙派推理拆成两条独立部署路线。
          </p>
        </div>
        <div className="overview-current-model">
          <span>Current package</span>
          <strong>{selectedPackage || "等待模型导入"}</strong>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <button
          type="button"
          onClick={() => {
            onSelectDeployMode("local");
            onSelectPanel("pipeline");
          }}
          className={`rounded-[30px] border p-6 text-left transition hover:-translate-y-1 ${deployMode === "local" ? "border-cyan-300/40 bg-cyan-300/10" : "border-white/10 bg-white/[0.035] hover:border-cyan-300/25"}`}
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="product-kicker">Main flow</div>
              <h3 className="mt-2 text-2xl font-black text-white">本地推理部署</h3>
            </div>
            <span className="rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100">Windows / macOS / Linux</span>
          </div>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            用户上传自己训练好的模型，工具自动转换、分析任务类型，提示上传合适输入，在本机完成推理并生成可视化报告。
          </p>
          <div className="mt-5 grid gap-2">
            {localSteps.map((step, idx) => (
              <div key={step} className="flex items-center gap-3 text-sm text-slate-300">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-300/10 text-xs font-bold text-cyan-100">{idx + 1}</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </button>

        <button
          type="button"
          onClick={() => {
            onSelectDeployMode("board");
            onSelectPanel("pipeline");
          }}
          className={`rounded-[30px] border p-6 text-left transition hover:-translate-y-1 ${deployMode === "board" ? "border-pink-200/40 bg-pink-200/10" : "border-white/10 bg-white/[0.035] hover:border-pink-200/25"}`}
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="product-kicker">Optional flow</div>
              <h3 className="mt-2 text-2xl font-black text-white">香橙派推理部署</h3>
            </div>
            <span className="rounded-full border border-pink-200/25 bg-pink-200/10 px-3 py-1 text-xs font-bold text-pink-100">高级可选</span>
          </div>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            保留板端部署能力，但不作为主线。只有选择该流程后，Pipeline 才显示打包、同步、板端运行等步骤。
          </p>
          <div className="mt-5 grid gap-2">
            {boardSteps.map((step, idx) => (
              <div key={step} className="flex items-center gap-3 text-sm text-slate-300">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-pink-200/10 text-xs font-bold text-pink-100">{idx + 1}</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        {[
          ["models", "Models", "管理模型资产"],
          ["infer-result", "Inference", "查看推理结果"],
          ["reports", "Reports", "预览和下载报告"],
          ["runtime", "Runtime", "输出和任务日志"],
        ].map(([id, title, desc]) => (
          <button key={id} type="button" onClick={() => onSelectPanel(id as WorkspacePanel)} className="rounded-2xl border border-white/10 bg-black/20 p-4 text-left transition hover:border-cyan-300/30 hover:bg-cyan-300/10">
            <div className="text-sm font-black text-white">{title}</div>
            <div className="mt-1 text-xs text-slate-400">{desc}</div>
          </button>
        ))}
      </div>
    </section>
  );
}
