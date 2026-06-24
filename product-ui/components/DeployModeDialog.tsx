"use client";

export type DeployMode = "local" | "board";

const modeCards: Array<{
  mode: DeployMode;
  title: string;
  badge: string;
  desc: string;
  bullets: string[];
}> = [
  {
    mode: "local",
    title: "本地推理",
    badge: "Local first",
    desc: "在当前电脑完成模型转换、输入准备、本地推理、结果可视化和报告导出。适合后续 Windows / macOS / Linux x86 / Linux ARM 软件包主流程。",
    bullets: ["自动读取 model_task.json", "按数字识别 / 图像分类 / 检测等任务提示输入", "输出 task_result.json、report.md、report.pdf"],
  },
  {
    mode: "board",
    title: "香橙派推理",
    badge: "Optional board flow",
    desc: "保留为可选高级流程。只有用户明确选择时才显示打包、同步、板端运行和板端报告，不再和本地推理混在同一页。",
    bullets: ["Package / Board Sync / Board Run", "读取 board report", "不影响本地 package 报告"],
  },
];

export function DeployModeDialog({
  open,
  onClose,
  onSelect,
  packageName,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (mode: DeployMode) => void;
  packageName?: string;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/72 p-6 backdrop-blur-md">
      <div className="w-full max-w-5xl rounded-[32px] border border-white/10 bg-[#0b1020] p-6 shadow-2xl shadow-black/50">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="product-kicker">Deploy mode</div>
            <h2 className="mt-2 text-2xl font-black text-white">请选择部署方式</h2>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
              模型已进入本地 package 流程。接下来只显示你选择的推理方式，避免本地推理和香橙派推理混在同一个 Pipeline 中。
            </p>
            {packageName ? <p className="mt-2 text-xs text-slate-500">当前 package：<span className="font-mono text-cyan-100">{packageName}</span></p> : null}
          </div>
          <button type="button" onClick={onClose} className="rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-slate-200">
            稍后选择
          </button>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {modeCards.map((item) => (
            <button
              key={item.mode}
              type="button"
              onClick={() => onSelect(item.mode)}
              className="group rounded-[28px] border border-white/10 bg-white/[0.035] p-5 text-left transition hover:-translate-y-1 hover:border-cyan-300/35 hover:bg-cyan-300/10"
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-xl font-black text-white">{item.title}</h3>
                <span className="rounded-full border border-pink-200/25 bg-pink-200/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.22em] text-pink-100">
                  {item.badge}
                </span>
              </div>
              <p className="mt-3 text-sm leading-7 text-slate-300">{item.desc}</p>
              <div className="mt-4 space-y-2 text-sm text-slate-300">
                {item.bullets.map((bullet) => (
                  <div key={bullet} className="flex gap-2">
                    <span className="text-cyan-200">•</span>
                    <span>{bullet}</span>
                  </div>
                ))}
              </div>
              <div className="mt-5 text-sm font-bold text-cyan-100">选择 {item.title} →</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function DeployModeSwitch({
  mode,
  onSelect,
}: {
  mode: DeployMode | null;
  onSelect: (mode: DeployMode) => void;
}) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="product-kicker">Deploy route</div>
          <h2 className="mt-1 text-xl font-black text-white">当前推理流程</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">选择后页面只显示对应流程。本地推理是主线，香橙派推理保留为可选流程。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onSelect("local")}
            className={`rounded-xl border px-4 py-2 text-xs font-bold ${mode === "local" ? "border-cyan-300/40 bg-cyan-300/15 text-cyan-100" : "border-white/10 bg-black/25 text-slate-300"}`}
          >
            本地推理
          </button>
          <button
            type="button"
            onClick={() => onSelect("board")}
            className={`rounded-xl border px-4 py-2 text-xs font-bold ${mode === "board" ? "border-cyan-300/40 bg-cyan-300/15 text-cyan-100" : "border-white/10 bg-black/25 text-slate-300"}`}
          >
            香橙派推理
          </button>
        </div>
      </div>
    </div>
  );
}
