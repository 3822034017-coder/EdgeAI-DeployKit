type JobLike = {
  action?: string | null;
  status?: string | null;
  code?: number | null;
  command?: string | string[] | null;
  log?: string | string[] | null;
};

function formatCommand(command?: string | string[] | null) {
  if (Array.isArray(command)) {
    return command.join(" ");
  }

  if (typeof command === "string" && command.trim()) {
    return command;
  }

  return "edgeai runtime status";
}

function formatValue(value?: string | null, fallback = "ready") {
  if (typeof value === "string" && value.trim()) {
    return value;
  }

  return fallback;
}

export function RuntimeConsolePreview({
  jobs = [],
}: {
  health?: unknown;
  jobs?: JobLike[];
}) {
  const latestJob = jobs?.[0];

  const status = formatValue(latestJob?.status, "ready");
  const action = formatValue(latestJob?.action, "runtime");
  const command = formatCommand(latestJob?.command);
  const code = latestJob?.code ?? 0;

  return (
    <section className="runtime-console-preview runtime-console-preview-clean">
      <div className="runtime-console-copy">
        <div className="product-kicker">Runtime Console</div>
        <h2>Runtime output</h2>

        <div className="runtime-mini-facts">
          <div>
            <span>Latest action</span>
            <strong>{action}</strong>
          </div>

          <div>
            <span>Status</span>
            <strong>{status}</strong>
          </div>
        </div>
      </div>

      <div className="runtime-terminal-card">
        <div className="runtime-terminal-head">
          <span />
          <span />
          <span />
          <strong>edgeai-runtime</strong>
        </div>

        <pre>{`$ ${command}
[status] ${status}
[action] ${action}
[code] ${code}
[ready] waiting for next command`}</pre>
      </div>
    </section>
  );
}
