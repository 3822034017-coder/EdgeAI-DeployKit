type MinimalModel = {
  name?: string;
  path?: string;
};

const steps = [
  {
    code: "01",
    title: "ONNX",
    desc: "Load model",
  },
  {
    code: "02",
    title: "Check",
    desc: "Validate graph",
  },
  {
    code: "03",
    title: "Package",
    desc: "Prepare assets",
  },
  {
    code: "04",
    title: "Sync",
    desc: "Sync to board",
  },
  {
    code: "05",
    title: "ATC",
    desc: "Convert to OM",
  },
  {
    code: "06",
    title: "Run",
    desc: "Run on AIPro",
  },
  {
    code: "07",
    title: "Report",
    desc: "Collect report",
  },
];

export function DeploymentFlowVisual({
  selectedModel,
}: {
  selectedModel?: MinimalModel;
}) {
  return (
    <section className="deployment-flow-panel">
      <div className="deployment-flow-head">
        <div>
          <div className="product-kicker">Deployment Flow</div>
          <h2>ONNX to AIPro flow</h2>
          <p>
            A clean view of the deployment path from local model validation to
            OrangePi AIPro runtime output.
          </p>
        </div>

        <div className="deployment-flow-model">
          <span>Model</span>
          <strong>{selectedModel?.name || "model.onnx"}</strong>
        </div>
      </div>

      <div className="deployment-flow-rail">
        {steps.map((step, index) => (
          <div key={step.code} className="deployment-flow-step">
            <div className="flow-step-index">{step.code}</div>
            <div>
              <h3>{step.title}</h3>
              <p>{step.desc}</p>
            </div>
            {index < steps.length - 1 && <div className="flow-step-link">→</div>}
          </div>
        ))}
      </div>
    </section>
  );
}
