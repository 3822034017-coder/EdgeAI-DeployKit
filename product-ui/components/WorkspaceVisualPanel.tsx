type MinimalModel = {
  name?: string;
  path?: string;
};

export function WorkspaceVisualPanel({
  selectedModel,
}: {
  selectedModel?: MinimalModel;
}) {
  return (
    <aside className="workspace-visual-panel">
      <div className="visual-image-frame">
        <img
          src="/images/edgeai-welcome.png"
          alt="EdgeAI connected workspace"
          loading="lazy"
          decoding="async"
        />
        <div className="visual-image-shade" />
        <div className="visual-caption">
          <span>Connected target</span>
          <strong>OrangePi AIPro</strong>
        </div>
      </div>

      <div className="edge-flow">
        <div className="edge-flow-node">
          <span>01</span>
          <strong>ONNX</strong>
        </div>
        <div className="edge-flow-arrow">→</div>
        <div className="edge-flow-node">
          <span>02</span>
          <strong>Package</strong>
        </div>
        <div className="edge-flow-arrow">→</div>
        <div className="edge-flow-node edge-flow-node-active">
          <span>03</span>
          <strong>AIPro</strong>
        </div>
      </div>

      <div className="visual-status-list">
        <div>
          <span>Current model</span>
          <strong>{selectedModel?.name || "model.onnx"}</strong>
        </div>
        <div>
          <span>Runtime target</span>
          <strong>Ascend 310B4</strong>
        </div>
        <div>
          <span>Board flow</span>
          <strong>SSH · ATC · OM · Run</strong>
        </div>
      </div>
    </aside>
  );
}
