type ModelLike = {
  name?: string;
  path?: string;
};

const metrics = [
  {
    label: "p50 latency",
    value: "Baseline",
    hint: "typical inference",
  },
  {
    label: "p95 latency",
    value: "Tail",
    hint: "worst-case signal",
  },
  {
    label: "Memory",
    value: "Track",
    hint: "runtime usage",
  },
  {
    label: "Target",
    value: "AIPro",
    hint: "board comparison",
  },
];

const stages = [
  "Select model",
  "Warmup",
  "Measure",
  "Compare",
  "Report",
];

export function BenchmarkProductPanel({
  selectedModel,
}: {
  selectedModel?: ModelLike;
  matrix?: unknown;
}) {
  return (
    <section className="benchmark-product-panel benchmark-product-panel-clean">
      <div className="benchmark-clean-copy">
        <div className="product-kicker">Performance Lab</div>

        <h2>Benchmark workspace</h2>

        <p>
          部署前先确认模型的延迟、尾延迟和内存表现。Benchmark 页只保留性能相关信息，
          环境检查统一放到 Runtime 页面。
        </p>

        <div className="benchmark-model-context">
          <span>Target model</span>
          <strong>{selectedModel?.path || "models/zoo/mnist/model.onnx"}</strong>
        </div>
      </div>

      <div className="benchmark-clean-board">
        <div className="benchmark-clean-board-head">
          <div>
            <span>Test profile</span>
            <strong>Local benchmark → AIPro readiness</strong>
          </div>

          <em>Recharts below</em>
        </div>

        <div className="benchmark-kpi-strip">
          {metrics.map((item) => (
            <div key={item.label} className="benchmark-kpi-card">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <em>{item.hint}</em>
            </div>
          ))}
        </div>

        <div className="benchmark-flow-strip">
          {stages.map((stage, index) => (
            <div key={stage} className="benchmark-flow-chip">
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{stage}</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
