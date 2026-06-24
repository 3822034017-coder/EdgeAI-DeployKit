"use client";

import React from "react";
import { API_BASE } from "@/lib/api";

const { useEffect, useMemo, useState } = React;

type RunMode = "local" | "board";

type ArtifactLike = {
  name?: string;
  path?: string;
  url?: string;
  kind?: string;
  type?: string;
  [key: string]: unknown;
};

const ACTIVE_RUN_KEY = "edgeai.currentRun";
const ACTIVE_LOCAL_KEYS = [
  "edgeai.activeLocalSession",
  "edgeai.activeLocalRunSession",
  "edgeai.localRun.session",
  "edgeai.localRunSession",
  "edgeai.active.local.session",
];

function cleanName(value: unknown) {
  return String(value || "")
    .trim()
    .replace(/\\/g, "/")
    .split("/")
    .filter(Boolean)
    .pop()
    ?.replace(/\.onnx$/i, "")
    .replace(/[^a-zA-Z0-9_.-]+/g, "_")
    .replace(/^_+|_+$/g, "") || "";
}

function safeJson(value: string | null) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function extractPackageName(value: unknown): string {
  if (!value) return "";
  if (typeof value === "string") return cleanName(value);
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = extractPackageName(item);
      if (found) return found;
    }
    return "";
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const direct =
      obj.packageName ||
      obj.package_name ||
      obj.package ||
      obj.model_name ||
      obj.modelName ||
      obj.name;
    const directClean = cleanName(direct);
    if (directClean) return directClean;

    const pathLike = obj.packageDir || obj.package_dir || obj.outputDir || obj.output_dir || obj.modelPath || obj.model_path;
    const pathClean = cleanName(pathLike);
    if (pathClean) return pathClean;

    for (const item of Object.values(obj)) {
      const found = extractPackageName(item);
      if (found) return found;
    }
  }
  return "";
}

function readActiveLocalPackage() {
  if (typeof window === "undefined") return "";

  for (const key of ACTIVE_LOCAL_KEYS) {
    const found = extractPackageName(safeJson(window.localStorage.getItem(key)) || window.localStorage.getItem(key));
    if (found) return found;
  }

  // Some earlier patches used slightly different key names. Scan only EdgeAI/local/session-looking entries.
  try {
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const key = window.localStorage.key(i) || "";
      const lower = key.toLowerCase();
      if (!lower.includes("edgeai") && !lower.includes("local")) continue;
      if (!lower.includes("session") && !lower.includes("run")) continue;
      const found = extractPackageName(safeJson(window.localStorage.getItem(key)) || window.localStorage.getItem(key));
      if (found) return found;
    }
  } catch {
    // ignore
  }
  return "";
}

function readPreferredRun() {
  if (typeof window === "undefined") return { mode: "local" as RunMode, packageName: "" };
  const data = safeJson(window.localStorage.getItem(ACTIVE_RUN_KEY));
  if (data && typeof data === "object") {
    const obj = data as { mode?: RunMode; packageName?: string };
    if (obj.mode === "board") return { mode: "board" as RunMode, packageName: "" };
    if (obj.mode === "local") return { mode: "local" as RunMode, packageName: cleanName(obj.packageName) };
  }
  const local = readActiveLocalPackage();
  return { mode: "local" as RunMode, packageName: local };
}

function writePreferredRun(mode: RunMode, packageName: string) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      ACTIVE_RUN_KEY,
      JSON.stringify({ mode, packageName: cleanName(packageName), updatedAt: Date.now() }),
    );
  } catch {
    // ignore
  }
}

function mdUrl(mode: RunMode, packageName: string, tick: number) {
  const q = new URLSearchParams({ mode, t: String(tick) });
  if (packageName) q.set("package_name", packageName);
  // Markdown route is intentionally v2: it is the stable route already used by the working Markdown preview.
  return `${API_BASE}/api/current-run-report-v2?${q.toString()}`;
}

function pdfUrl(mode: RunMode, packageName: string, tick: number) {
  const q = new URLSearchParams({ mode, force: "1", t: String(tick) });
  if (packageName) q.set("package_name", packageName);
  return `/api/current-run-report-pdf?${q.toString()}`;
}

function compact(text: string, max = 92) {
  if (!text || text.length <= max) return text;
  return `${text.slice(0, 38)}...${text.slice(-Math.max(12, max - 44))}`;
}

function boardReportHint(artifacts: ArtifactLike[]) {
  const reports = (artifacts || []).filter((item: ArtifactLike) => String(item.path || item.name || "").includes("edgeai_report"));
  return String(reports[0]?.path || "reports/edgeai_report.md / reports/edgeai_report.pdf");
}

function pickLatestPackageFromList(data: unknown): string {
  const list = Array.isArray(data)
    ? data
    : Array.isArray((data as any)?.reports)
      ? (data as any).reports
      : Array.isArray((data as any)?.items)
        ? (data as any).items
        : Array.isArray((data as any)?.data)
          ? (data as any).data
          : [];

  for (const item of list) {
    const name = extractPackageName(item);
    if (name) return name;
  }
  return "";
}

export function CurrentRunReportPanel({ artifacts = [] }: { artifacts?: ArtifactLike[] }) {
  const preferred = useMemo(() => readPreferredRun(), []);
  const [mode, setMode] = useState(preferred.mode as RunMode);
  const [packageName, setPackageName] = useState(preferred.packageName as string);
  const [content, setContent] = useState("" as string);
  const [error, setError] = useState("" as string);
  const [loading, setLoading] = useState(false as boolean);
  const [view, setView] = useState("markdown" as "markdown" | "pdf");
  const [tick, setTick] = useState(Date.now() as number);
  const [pdfSrc, setPdfSrc] = useState("" as string);

  const isLocal = mode === "local";
  const reportHint = useMemo(() => boardReportHint(artifacts), [artifacts]);

  async function resolveLatestLocalPackage() {
    const active = readActiveLocalPackage();
    if (active) return active;
    try {
      const res = await fetch(`${API_BASE}/api/package-local-reports?t=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) return "";
      return pickLatestPackageFromList(await res.json());
    } catch {
      return "";
    }
  }

  async function ensureLocalPackage(current: string) {
    if (mode !== "local") return current;
    if (cleanName(current)) return cleanName(current);
    const latest = await resolveLatestLocalPackage();
    if (latest) {
      setPackageName(latest);
      writePreferredRun("local", latest);
    }
    return latest;
  }

  async function refreshMarkdown() {
    setLoading(true);
    setError("");
    const nextTick = Date.now();
    setTick(nextTick);
    try {
      const nextPackage = await ensureLocalPackage(packageName);
      const res = await fetch(mdUrl(mode, nextPackage, nextTick), { cache: "no-store" });
      if (!res.ok) throw new Error(await res.text());
      setContent(await res.text());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setContent("");
    } finally {
      setLoading(false);
    }
  }

  async function openPdfPreview() {
    setError("");
    try {
      const nextPackage = await ensureLocalPackage(packageName);
      const nextTick = Date.now();
      const url = pdfUrl(mode, nextPackage, nextTick);
      setTick(nextTick);
      setPdfSrc(url);
      setView("pdf");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function openPdfInNewTab() {
    setError("");
    try {
      const nextPackage = await ensureLocalPackage(packageName);
      const nextTick = Date.now();
      const url = pdfUrl(mode, nextPackage, nextTick);
      setTick(nextTick);
      setPdfSrc(url);
      // Open the same URL used by the iframe preview. This avoids stale direct backend URLs.
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function syncFromLocalSession() {
    const latest = await resolveLatestLocalPackage();
    if (latest) {
      setMode("local");
      setPackageName(latest);
      writePreferredRun("local", latest);
      setView("markdown");
      setPdfSrc("");
      setTick(Date.now());
      return;
    }
    setError("没有找到当前本地推理 package。请先完成 Pipeline 的 01~05 本地推理流程。");
  }

  function switchMode(nextMode: RunMode) {
    if (nextMode === "local") {
      const local = readActiveLocalPackage() || packageName;
      const nextPackage = cleanName(local);
      setMode("local");
      setPackageName(nextPackage);
      writePreferredRun("local", nextPackage);
    } else {
      setMode("board");
      setPackageName("");
      writePreferredRun("board", "");
    }
    setView("markdown");
    setPdfSrc("");
    setTick(Date.now());
  }

  useEffect(() => {
    refreshMarkdown();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, packageName]);

  return (
    <section className="workspace-panel-card workspace-panel-card-large p-5">
      <div className="report-preview-head">
        <div>
          <div className="product-kicker">Current Run Report</div>
          <h2>当前运行报告</h2>
          <p>当前报告跟随运行后端：本地模式读取 package 报告；香橙派模式读取 board 报告。PDF 预览和下载统一走同一条 v4 链路。</p>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => switchMode("local")} className={`rounded-xl border px-3 py-2 text-xs font-semibold ${isLocal ? "border-cyan/50 bg-cyan/15 text-cyan" : "border-line bg-black/30 text-ink"}`}>
          本地 ONNX Runtime
        </button>
        <button type="button" onClick={() => switchMode("board")} className={`rounded-xl border px-3 py-2 text-xs font-semibold ${!isLocal ? "border-cyan/50 bg-cyan/15 text-cyan" : "border-line bg-black/30 text-ink"}`}>
          香橙派 / Board
        </button>
        <button type="button" onClick={syncFromLocalSession} className="rounded-xl border border-line bg-black/30 px-3 py-2 text-xs text-ink">
          跟随当前本地流程
        </button>
        <button type="button" onClick={refreshMarkdown} className="rounded-xl border border-line bg-black/30 px-3 py-2 text-xs text-ink" disabled={loading}>
          {loading ? "刷新中" : "刷新 Markdown"}
        </button>
        <button type="button" onClick={openPdfPreview} className="rounded-xl border border-cyan/30 bg-cyan/10 px-3 py-2 text-xs text-cyan">
          PDF 预览
        </button>
        <button type="button" onClick={openPdfInNewTab} className="rounded-xl border border-cyan/30 bg-cyan/10 px-3 py-2 text-xs text-cyan">
          打开 PDF
        </button>
      </div>

      <div className="mb-4 rounded-2xl border border-line bg-black/20 p-3 text-xs leading-6 text-muted">
        <div>当前模式：<span className="font-semibold text-ink">{isLocal ? "local-run 本地推理" : "board-run 香橙派推理"}</span></div>
        {isLocal ? (
          <>
            <div>
              当前 package：
              <input
                value={packageName}
                onChange={(event) => {
                  const next = cleanName(event.target.value);
                  setPackageName(next);
                  writePreferredRun("local", next);
                  setView("markdown");
                  setPdfSrc("");
                }}
                className="ml-2 rounded-lg border border-line bg-black/30 px-2 py-1 font-mono text-xs text-ink"
              />
            </div>
            <div>Markdown：<span className="font-mono text-muted">outputs/packages/{packageName || "<package>"}/report.md</span></div>
            <div>PDF：<span className="font-mono text-muted">outputs/packages/{packageName || "<package>"}/report.pdf</span></div>
          </>
        ) : (
          <>
            <div>Board 报告入口：<span className="font-mono text-muted">{compact(reportHint)}</span></div>
            <div>Board 模式只读取 reports/edgeai_report.md/pdf，不会覆盖本地 package 报告。</div>
          </>
        )}
      </div>

      {error ? <div className="mb-3 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">{error}</div> : null}

      <div className="mb-3 flex flex-wrap gap-2">
        <button type="button" onClick={() => setView("markdown")} className={`rounded-xl border px-3 py-2 text-xs ${view === "markdown" ? "border-cyan/30 bg-cyan/10 text-cyan" : "border-line bg-black/30 text-ink"}`}>
          Markdown
        </button>
        <button type="button" onClick={openPdfPreview} className={`rounded-xl border px-3 py-2 text-xs ${view === "pdf" ? "border-cyan/30 bg-cyan/10 text-cyan" : "border-line bg-black/30 text-ink"}`}>
          PDF
        </button>
        <a className="rounded-xl border border-line bg-black/30 px-3 py-2 text-xs text-ink" href={mdUrl(mode, packageName, tick)} target="_blank" rel="noreferrer">
          打开 Markdown
        </a>
      </div>

      {view === "pdf" ? (
        <div className="overflow-hidden rounded-2xl border border-line bg-black/30">
          {pdfSrc ? (
            <iframe key={pdfSrc} title="Current Run Report PDF" src={pdfSrc} className="h-[760px] w-full bg-white" />
          ) : (
            <div className="p-4 text-sm leading-6 text-muted">点击上方 PDF 预览后显示当前运行报告。</div>
          )}
        </div>
      ) : (
        <pre className="max-h-[760px] overflow-auto rounded-2xl border border-line bg-black/30 p-4 whitespace-pre-wrap font-mono text-xs leading-6 text-muted">
          {content || (loading ? "正在读取当前运行报告..." : "暂无当前运行报告。请先完成 local-report 或 board report。")}
        </pre>
      )}
    </section>
  );
}

export function ReportPreviewGrid({ artifacts = [] }: { artifacts?: ArtifactLike[] }) {
  return <CurrentRunReportPanel artifacts={artifacts} />;
}
