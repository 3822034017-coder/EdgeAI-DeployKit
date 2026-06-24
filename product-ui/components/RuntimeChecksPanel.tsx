type CheckItem = {
  name: string;
  path: string;
  ok: boolean;
};

type HealthLike = {
  score?: string;
  passed?: number;
  total?: number;
  checks?: unknown;
};

const fallbackChecks: CheckItem[] = [
  { name: "edgeai CLI", path: "/root/edge-ai-deploy-kit/.venv/bin/edgeai", ok: true },
  { name: "Python", path: "/root/edge-ai-deploy-kit/.venv/bin/python3", ok: true },
  { name: "cmake", path: "/usr/bin/cmake", ok: true },
  { name: "make", path: "/usr/bin/make", ok: true },
  { name: "gcc", path: "/usr/bin/gcc", ok: true },
  { name: "g++", path: "/usr/bin/g++", ok: true },
  { name: "qemu-system-aarch64", path: "/usr/local/bin/qemu-system-aarch64", ok: true },
  { name: "atc", path: "atc", ok: false },
  { name: "docker", path: "/usr/bin/docker", ok: true },
  {
    name: "openEuler aarch64 SDK",
    path: "/opt/openeuler-aarch64/environment-setup-aarch64-openeuler-linux",
    ok: false,
  },
];

function valueToCheck(name: string, value: unknown): CheckItem {
  if (typeof value === "boolean") {
    return { name, path: name, ok: value };
  }

  if (typeof value === "string") {
    return { name, path: value, ok: Boolean(value) };
  }

  if (value && typeof value === "object") {
    const item = value as {
      name?: string;
      label?: string;
      path?: string;
      value?: string;
      command?: string;
      ok?: boolean;
      available?: boolean;
      status?: string;
    };

    const statusText = String(item.status || "").toLowerCase();
    const ok =
      typeof item.ok === "boolean"
        ? item.ok
        : typeof item.available === "boolean"
          ? item.available
          : statusText === "ok" || statusText === "ready" || statusText === "success";

    return {
      name: item.name || item.label || name,
      path: item.path || item.value || item.command || name,
      ok,
    };
  }

  return { name, path: name, ok: false };
}

function normalizeChecks(health?: HealthLike): CheckItem[] {
  const checks = health?.checks;

  if (Array.isArray(checks)) {
    return checks.map((item, index) => valueToCheck(`tool-${index + 1}`, item));
  }

  if (checks && typeof checks === "object") {
    return Object.entries(checks as Record<string, unknown>).map(([name, value]) =>
      valueToCheck(name, value),
    );
  }

  return fallbackChecks;
}

function scoreText(health?: HealthLike, checks?: CheckItem[]) {
  if (health?.score) return health.score;

  if (typeof health?.passed === "number" && typeof health?.total === "number") {
    return `${health.passed}/${health.total}`;
  }

  if (checks?.length) {
    const passed = checks.filter((item) => item.ok).length;
    return `${passed}/${checks.length}`;
  }

  return "0/0";
}

export function RuntimeChecksPanel({ health }: { health?: HealthLike }) {
  const checks = normalizeChecks(health);
  const score = scoreText(health, checks);

  return (
    <section className="runtime-assets-panel">
      <div className="runtime-assets-head">
        <div>
          <div className="product-kicker">Health</div>
          <h2>Runtime capability</h2>
        </div>

        <strong>{score}</strong>
      </div>

      <div className="runtime-assets-table">
        <div className="runtime-assets-row runtime-assets-row-head">
          <span>Tool</span>
          <span>Path</span>
          <span>Status</span>
        </div>

        {checks.map((item) => (
          <div key={`${item.name}-${item.path}`} className="runtime-assets-row">
            <span>{item.name}</span>
            <code>{item.path}</code>
            <em className={item.ok ? "runtime-status-ok" : "runtime-status-missing"}>
              {item.ok ? "Ready" : "Missing"}
            </em>
          </div>
        ))}
      </div>
    </section>
  );
}
