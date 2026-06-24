"use client";

import * as React from "react";

type TopKItem = {
  rank?: number;
  index?: number | string | null;
  label?: string | null;
  score?: number | string | null;
};

type TaskResult = {
  ok?: boolean;
  package_name?: string;
  task_type?: string;
  task_title?: string;
  result_view?: string;
  input_prompt?: string;
  summary?: {
    title?: string;
    primary?: string;
    confidence?: number | string | null;
  };
  topk?: TopKItem[];
  latency_ms?: number | string | null;
  backend?: string | null;
  provider?: string | null;
  artifacts?: Record<string, string | null | undefined>;
};

function readActivePackage() {
  if (typeof window === "undefined") return "";

  const directKeys = [
    "edgeai.activePackage",
    "edgeai.activeLocalPackage",
    "edgeai.localPackage",
    "edgeai:activePackage",
    "edgeai:activeLocalPackage",
    "edgeai:activeLocalSession",
    "edgeai.activeLocalSession",
  ];

  for (const key of directKeys) {
    const raw = window.localStorage.getItem(key);
    if (!raw) continue;
    try {
      const obj = JSON.parse(raw);
      const value = obj?.package_name || obj?.packageName || obj?.package || obj?.name;
      if (typeof value === "string" && value.trim()) return value.trim();
    } catch {
      if (raw.trim() && !raw.includes("{") && !raw.includes("[")) return raw.trim();
    }
  }

  for (let i = 0; i < window.localStorage.length; i += 1) {
    const key = window.localStorage.key(i) || "";
    const raw = window.localStorage.getItem(key) || "";
    if (!raw.includes("package")) continue;
    try {
      const obj = JSON.parse(raw);
      const value = obj?.package_name || obj?.packageName || obj?.package || obj?.name;
      if (typeof value === "string" && value.trim()) return value.trim();
    } catch {
      // ignore non-json values
    }
  }

  return "";
}

function fmtScore(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  const n = Number(value);
  if (Number.isFinite(n)) return n.toFixed(4);
  return String(value);
}

export function TaskResultPanel(props: { packageName?: string }) {
  const [packageName, setPackageName] = React.useState(props.packageName || "");
  const [data, setData] = React.useState(null as TaskResult | null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");

  async function refresh() {
    const nextPackage = props.packageName || packageName || readActivePackage();
    setPackageName(nextPackage);
    if (!nextPackage) {
      setError("尚未检测到当前 package。请先完成 Convert / Analyze / Local Run，或刷新任务信息。");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const url = `/api/local-task-result?package_name=${encodeURIComponent(nextPackage)}&force=1&t=${Date.now()}`;
      const resp = await fetch(url, { cache: "no-store" });
      const text = await resp.text();
      let json: any = null;
      try {
        json = JSON.parse(text);
      } catch {
        throw new Error(text.slice(0, 300) || `HTTP ${resp.status}`);
      }
      if (!resp.ok) throw new Error(json?.detail || `HTTP ${resp.status}`);
      setData(json as TaskResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => {
    const next = props.packageName || readActivePackage();
    if (next) setPackageName(next);
  }, [props.packageName]);

  React.useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.packageName]);

  const topk = data?.topk || [];

  return (
    <section className="rounded-[28px] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-black/25">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-black uppercase tracking-[0.32em] text-pink-200/80">Task Result Renderer</div>
          <h2 className="mt-2 text-2xl font-black text-white">任务化推理结果</h2>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
            系统会读取 model_task.json 与 local_result.json，按数字识别、图像分类、检测等任务类型生成更易理解的结果视图。
          </p>
        </div>
        <button
          type="button"
          onClick={refresh}
          className="rounded-xl border border-cyan-300/25 bg-cyan-300/10 px-4 py-2 text-xs font-bold text-cyan-100 hover:bg-cyan-300/20"
        >
          {loading ? "刷新中..." : "刷新结果"}
        </button>
      </div>

      {error ? (
        <div className="mt-5 rounded-2xl border border-rose-300/20 bg-rose-500/10 p-4 text-sm leading-6 text-rose-100">
          {error}
        </div>
      ) : null}

      {data ? (
        <div className="mt-5 grid gap-4">
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Package</div>
              <div className="mt-2 text-lg font-bold text-white">{data.package_name || packageName}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Task</div>
              <div className="mt-2 text-lg font-bold text-emerald-200">{data.task_title || data.task_type || "unknown"}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Runtime</div>
              <div className="mt-2 text-sm font-bold text-slate-200">
                {data.backend || "onnxruntime"} / {data.provider || "CPU"}
              </div>
              <div className="mt-1 text-xs text-slate-500">latency: {fmtScore(data.latency_ms)} ms</div>
            </div>
          </div>

          <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-5">
            <div className="text-xs uppercase tracking-[0.25em] text-cyan-100/80">Result Summary</div>
            <div className="mt-2 text-xl font-black text-white">{data.summary?.title || "推理结果"}</div>
            <div className="mt-2 text-base font-bold text-cyan-50">{data.summary?.primary || "已生成任务化推理结果。"}</div>
            <div className="mt-2 text-sm text-slate-300">confidence / score: {fmtScore(data.summary?.confidence)}</div>
          </div>

          {topk.length ? (
            <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/25">
              <div className="border-b border-white/10 px-5 py-3 text-xs uppercase tracking-[0.25em] text-slate-400">TopK</div>
              <div className="divide-y divide-white/5">
                {topk.slice(0, 8).map((item, idx) => (
                  <div key={`${item.rank || idx}-${item.index}`} className="grid grid-cols-[70px_1fr_110px] gap-3 px-5 py-3 text-sm">
                    <div className="font-bold text-slate-400">#{item.rank || idx + 1}</div>
                    <div className="font-bold text-white">{item.label || item.index}</div>
                    <div className="text-right text-cyan-100">{fmtScore(item.score)}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
