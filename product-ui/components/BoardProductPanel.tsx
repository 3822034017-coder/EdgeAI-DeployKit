type MinimalModel = {
  name?: string;
  path?: string;
};

type HealthCheckLike = {
  name?: string;
  label?: string;
  key?: string;
  available?: boolean;
  status?: string;
  detail?: string;
  version?: string;
};

type HealthLike = {
  checks?: HealthCheckLike[];
};

type JobLike = {
  id?: string;
  action?: string;
  status?: string;
  created_at?: string;
};

function findCheck(health: HealthLike | undefined, keywords: string[]) {
  const checks = health?.checks || [];

  return checks.find((item) => {
    const text = [
      item.name,
      item.label,
      item.key,
      item.status,
      item.detail,
      item.version,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return keywords.some((keyword) => text.includes(keyword));
  });
}

function getStatus(check: HealthCheckLike | undefined) {
  if (!check) return "unknown";
  if (check.available) return "ready";
  return "missing";
}

function getStatusLabel(status: string) {
  if (status === "ready") return "Ready";
  if (status === "missing") return "Missing";
  return "Unknown";
}

export function BoardProductPanel({
  health,
  jobs,
  selectedModel,
}: {
  health?: HealthLike;
  jobs?: JobLike[];
  selectedModel?: MinimalModel;
}) {
  const ssh = findCheck(health, ["ssh"]);
  const atc = findCheck(health, ["atc"]);
  const qemu = findCheck(health, ["qemu"]);
  const docker = findCheck(health, ["docker"]);
  const lastJob = jobs?.[0];

  const items = [
    {
      label: "SSH link",
      value: "SSH access",
      status: getStatus(ssh),
    },
    {
      label: "ATC compiler",
      value: "ATC convert",
      status: getStatus(atc),
    },
    {
      label: "QEMU ARM64",
      value: "QEMU ready",
      status: getStatus(qemu),
    },
    {
      label: "Docker",
      value: "Docker ready",
      status: getStatus(docker),
    },
  ];

  return (
    <section className="board-product-panel">
      <div className="board-product-copy">
        <div className="product-kicker">Board Session</div>
        <h2>OrangePi AIPro target</h2>
        <p>
          Prepare the selected ONNX model for board-side conversion, transfer and
          execution. The panel focuses on real deployment dependencies instead of
          decorative visuals.
        </p>

        <div className="board-product-model">
          <span>Model path</span>
          <strong>{selectedModel?.path || "models/zoo/mnist/model.onnx"}</strong>
        </div>
      </div>

      <div className="board-product-visual" aria-hidden="true">
        <div className="board-device-shell">
          <div className="board-chip">Ascend 310B4</div>
          <div className="board-port-row">
            <span />
            <span />
            <span />
            <span />
          </div>
          <div className="board-device-name">OrangePi AIPro</div>
        </div>
        <div className="board-cable-line" />
        <div className="board-host-card">
          <span>Host</span>
          <strong>EdgeAI CLI</strong>
        </div>
      </div>

      <div className="board-status-grid">
        {items.map((item) => (
          <div key={item.label} className="board-status-card">
            <div className={`status-dot status-${item.status}`} />
            <div>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <em>{getStatusLabel(item.status)}</em>
            </div>
          </div>
        ))}
      </div>

      <div className="board-job-strip">
        <span>Latest job</span>
        <strong>{lastJob?.action || "No active board job"}</strong>
        <em>{lastJob?.status || "idle"}</em>
      </div>
    </section>
  );
}
