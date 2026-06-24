type ModelLike = {
  name?: string;
  path?: string;
  type?: string;
  source?: string;
  size_mb?: number;
  size?: number | string;
};

function getModelName(model?: ModelLike) {
  return model?.name || model?.path?.split("/").pop() || "model.onnx";
}

function getModelSize(model?: ModelLike) {
  if (typeof model?.size_mb === "number") {
    return `${model.size_mb.toFixed(2)} MB`;
  }

  if (typeof model?.size === "number") {
    return `${(model.size / 1024 / 1024).toFixed(2)} MB`;
  }

  if (typeof model?.size === "string") {
    return model.size;
  }

  return "Unknown";
}

export function ModelProductPanel({
  selectedModel,
  models = [],
}: {
  selectedModel?: ModelLike;
  models?: ModelLike[];
}) {
  const name = getModelName(selectedModel);

  return (
    <section className="model-product-panel">
      <div className="model-product-copy">
        <div className="product-kicker">Model Asset</div>
        <h2>ONNX model asset</h2>
        <p>
          Keep model selection, metadata inspection and validation in one focused
          interface before starting deployment.
        </p>

        <div className="model-product-path">
          <span>Model path</span>
          <strong>{selectedModel?.path || "models/zoo/mnist/model.onnx"}</strong>
        </div>
      </div>

      <div className="model-graph-card" aria-hidden="true">
        <div className="model-graph-title">
          <span>Graph preview</span>
          <strong>{name}</strong>
        </div>

        <div className="model-graph">
          <div className="model-node model-node-input">Input</div>
          <div className="model-link" />
          <div className="model-node model-node-core">ONNX</div>
          <div className="model-link" />
          <div className="model-node model-node-output">Output</div>
        </div>
      </div>

      <div className="model-stat-grid">
        <div className="model-stat-card">
          <span>Registry</span>
          <strong>{models.length}</strong>
          <em>models</em>
        </div>

        <div className="model-stat-card">
          <span>Format</span>
          <strong>{selectedModel?.type || "ONNX"}</strong>
          <em>format</em>
        </div>

        <div className="model-stat-card">
          <span>Size</span>
          <strong>{getModelSize(selectedModel)}</strong>
          <em>asset size</em>
        </div>

        <div className="model-stat-card">
          <span>Source</span>
          <strong>{selectedModel?.source || "workspace"}</strong>
          <em>source</em>
        </div>
      </div>
    </section>
  );
}
