import type { WorkspacePanel } from "./AppShell";
import { WorkspaceVisualPanel } from "./WorkspaceVisualPanel";

type MinimalModel = {
  name?: string;
  path?: string;
};

const features: Array<{
  id: WorkspacePanel;
  num: string;
  title: string;
  desc: string;
  tone: string;
}> = [
  {
    id: "models",
    num: "01",
    title: "Models",
    desc: "管理 ONNX 模型和元数据。",
    tone: "pink",
  },
  {
    id: "pipeline",
    num: "02",
    title: "Pipeline",
    desc: "执行打包、同步和部署步骤。",
    tone: "violet",
  },
  {
    id: "benchmark",
    num: "03",
    title: "Benchmark",
    desc: "测量延迟、p50 / p95 和内存。",
    tone: "cyan",
  },
  {
    id: "board",
    num: "04",
    title: "OrangePi",
    desc: "查看 AIPro 板端部署状态。",
    tone: "amber",
  },
  {
    id: "reports",
    num: "05",
    title: "Reports",
    desc: "预览矩阵和部署报告。",
    tone: "rose",
  },
  {
    id: "runtime",
    num: "06",
    title: "Runtime",
    desc: "检查 QEMU、Docker、ATC 和任务日志。",
    tone: "blue",
  },
];

export function FeatureLaunchGrid({
  selectedModel,
  onSelectPanel,
}: {
  selectedModel?: MinimalModel;
  onRefresh?: () => void;
  onSelectPanel?: (panel: WorkspacePanel) => void;
}) {
  return (
    <section className="overview-command-center">
      <div className="overview-command-head">
        <div>
          <div className="overview-kicker">Command Center</div>
          <h2>Choose a module.</h2>
          <p>
            Choose one workspace at a time. The operation panel stays clean,
            readable and closer to a real deployment product.
          </p>
        </div>

        <div className="overview-current-model">
          <span>Selected model</span>
          <strong>{selectedModel?.path || "models/zoo/mnist/model.onnx"}</strong>
        </div>
      </div>

      <div className="overview-command-body">
        <div className="overview-launch-grid">
          {features.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectPanel?.(item.id)}
              className={`overview-launch-card overview-launch-${item.tone}`}
            >
              <div className="overview-launch-num">{item.num}</div>

              <div>
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </div>

              <div className="overview-launch-arrow">→</div>
            </button>
          ))}
        </div>

        <WorkspaceVisualPanel selectedModel={selectedModel} />
      </div>
    </section>
  );
}
