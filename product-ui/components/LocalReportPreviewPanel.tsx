"use client";

import React from "react";
import { API_BASE } from "@/lib/api";
import type { ModelItem } from "@/lib/types";
import { Badge, SectionTitle, Surface } from "./ui";

type ArtifactLike = Record<string, any>;
type ModelLike = any;
type LocalReportPreviewPanelProps = {
  artifacts?: ArtifactLike[];
  selectedModel?: ModelLike;
  running?: boolean;
  onRefresh?: () => void | Promise<void>;
};
const { useEffect, useMemo, useState } = React;
const ACTIVE_SESSION_KEY = "edgeai.activeLocalSession.v1";

type PackageLocalReport = {
  model_name: string;
  report_path: string;
  pdf_path?: string | null;
  has_pdf?: boolean;
  source?: string;
  size_bytes?: number;
  pdf_size_bytes?: number | null;
  modified_time?: number;
  pdf_modified_time?: number | null;
  modified_at?: string;
};

type ActiveLocalSession = {
  modelPath?: string;
  packageName?: string;
  testInput?: string;
  status?: string;
  updatedAt?: number;
};

function cleanName(value: string | undefined) {
  const raw = (value || "user_model").replace(/\.onnx$/i, "");
  const cleaned = raw.replace(/[^A-Za-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
  return cleaned || "user_model";
}

function basenameWithoutExt(path?: string) {
  if (!path) return "user_model";
  const clean = path.replace(/\\/g, "/");
  const parts = clean.split("/").filter(Boolean);
  const file = parts[parts.length - 1] || "user_model";
  const parent = parts[parts.length - 2] || "user_model";
  const stem = file.replace(/\.onnx$/i, "").replace(/\.(pt|pth|h5|keras|pb)$/i, "");
  if (stem === "model" || stem.startsWith("model_")) return cleanName(parent);
  return cleanName(stem);
}

function selectedPackageName(model?: ModelItem) {
  const path = ((model as (ModelItem & { path?: string }) | undefined)?.path || "").trim();
  const name = ((model as (ModelItem & { name?: string }) | undefined)?.name || "").trim();
  return `${basenameWithoutExt(path || name)}_local`;
}

function readActiveSessionPackage() {
  if (typeof window === "undefined") return "";
  try {
    const raw = window.localStorage.getItem(ACTIVE_SESSION_KEY);
    if (!raw) return "";
    const data = JSON.parse(raw) as ActiveLocalSession;
    return cleanName(data.packageName || "");
  } catch {
    return "";
  }
}

function formatTime(value?: number | string | null) {
  if (!value) return "未知";
  const n = typeof value === "number" ? value * 1000 : Date.parse(String(value));
  if (!Number.isFinite(n)) return String(value);
  return new Date(n).toLocaleString();
}

function formatBytes(size?: number | null) {
  if (!size) return "0 B";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(2)} MB`;
}

function packagePdfUrl(modelName: string, tick: number) {
  return `/api/current-run-report-pdf?mode=local&package_name=${encodeURIComponent(modelName)}&force=1&t=${tick}`;
}

function packageMarkdownUrl(modelName: string, tick: number) {
  return `${API_BASE}/api/package-local-reports/${encodeURIComponent(modelName)}?force=1&t=${tick}`;
}

async function fetchPackageReports(): Promise<PackageLocalReport[]> {
  const res = await fetch(`${API_BASE}/api/package-local-reports?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as PackageLocalReport[];
}

async function fetchPackageReportContent(name: string): Promise<string> {
  const res = await fetch(packageMarkdownUrl(name, Date.now()), { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return await res.text();
}

export function LocalReportPreviewPanel({
  artifacts = [],
  selectedModel,
  running = false,
  onRefresh,
}: LocalReportPreviewPanelProps) {
void running;
  void onRefresh;
const [reports, setReports] = useState([] as PackageLocalReport[]);
  const [selectedReport, setSelectedReport] = useState("" as string);
  const [content, setContent] = useState("" as string);
  const [loading, setLoading] = useState(false as boolean);
  const [error, setError] = useState("" as string);
  const [showPdf, setShowPdf] = useState(true as boolean);
  const [pdfTick, setPdfTick] = useState(Date.now() as number);
  const [activeSessionPackage, setActiveSessionPackage] = useState("" as string);

  const selectedDefaultPackage = useMemo(() => selectedPackageName(selectedModel), [selectedModel]);
  const preferredName = activeSessionPackage || selectedDefaultPackage;
  const current = reports.find((item: any) => item.model_name === selectedReport);
  const currentPdfUrl = selectedReport ? packagePdfUrl(selectedReport, pdfTick) : "";

  function refreshActiveSessionPackage() {
    setActiveSessionPackage(readActiveSessionPackage());
  }

  async function refreshReports(forcePdf = false) {
    setLoading(true);
    setError("");
    refreshActiveSessionPackage();
    if (forcePdf) setPdfTick(Date.now());

    try {
      const next = await fetchPackageReports();
      const activeName = readActiveSessionPackage();
      setActiveSessionPackage(activeName);
      setReports(next);

      const active = activeName ? next.find((item: any) => item.model_name === activeName) : undefined;
      const preferred = next.find((item: any) => item.model_name === preferredName);
      const keep = selectedReport ? next.find((item: any) => item.model_name === selectedReport) : undefined;
      const newest = next[0];
      const nextSelected = active?.model_name || preferred?.model_name || keep?.model_name || newest?.model_name || "";

      setSelectedReport(nextSelected);
      if (nextSelected) {
        setContent(await fetchPackageReportContent(nextSelected));
      } else {
        setContent("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadReport(name: string) {
    setSelectedReport(name);
    setShowPdf(true);
    setPdfTick(Date.now());
    setLoading(true);
    setError("");
    try {
      setContent(await fetchPackageReportContent(name));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setContent("");
    } finally {
      setLoading(false);
    }
  }

  function forceRefreshPdf() {
    setPdfTick(Date.now());
    setShowPdf(true);
  }

  useEffect(() => {
    refreshReports(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preferredName]);

  useEffect(() => {
    const onFocus = () => refreshReports(true);
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Surface className="p-5">
      <SectionTitle
        label="LOCAL REPORT"
        title="本地推理报告预览"
        description="Reports 默认跟随 Pipeline 中的本次本地推理流程 package，而不是旧的全局报告。PDF 直接读取 outputs/packages/<package>/report.pdf。"
        right={<Badge tone="cyan">Active session report</Badge>}
      />

      {activeSessionPackage ? (
        <div className="mb-4 rounded-2xl border border-cyan/20 bg-cyan/10 p-3 text-xs text-cyan">
          当前本地推理流程 package：<span className="font-mono text-ink">{activeSessionPackage}</span>
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedReport}
            onChange={(event) => loadReport(event.target.value)}
            className="min-h-[38px] min-w-[240px] rounded-xl border border-line bg-black/30 px-3 py-2 text-xs text-ink outline-none"
          >
            {reports.length ? (
              reports.map((item: any) => (
                <option key={item.model_name} value={item.model_name}>
                  {item.model_name}
                </option>
              ))
            ) : (
              <option value="">暂无 package report</option>
            )}
          </select>

          <button type="button" className="rounded-xl border border-line bg-black/30 px-3 py-2 text-xs text-ink" onClick={() => refreshReports(true)} disabled={loading}>
            {loading ? "刷新中" : "刷新并跟随本次流程"}
          </button>

          <button type="button" className="rounded-xl border border-cyan/30 bg-cyan/10 px-3 py-2 text-xs text-cyan" onClick={forceRefreshPdf} disabled={!selectedReport}>
            重新生成 PDF
          </button>

          <button type="button" className="rounded-xl border border-line bg-black/30 px-3 py-2 text-xs text-ink" onClick={() => setShowPdf((v: boolean) => !v)}>
            {showPdf ? "切换 Markdown" : "切换 PDF"}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {selectedReport ? (
            <a className="rounded-xl border border-line bg-black/30 px-3 py-2 text-xs text-ink" href={packageMarkdownUrl(selectedReport, Date.now())} target="_blank" rel="noreferrer">
              打开当前 Markdown
            </a>
          ) : null}
          {selectedReport ? (
            <a className="rounded-xl border border-cyan/30 bg-cyan/10 px-3 py-2 text-xs text-cyan" href={currentPdfUrl} target="_blank" rel="noreferrer">
              打开当前 PDF
            </a>
          ) : null}
        </div>
      </div>

      {current ? (
        <div className="mb-4 grid gap-2 rounded-2xl border border-line bg-black/20 p-3 md:grid-cols-5">
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted">Package</div>
            <div className="mt-1 break-all text-xs font-semibold text-ink">{current.model_name}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted">Markdown</div>
            <div className="mt-1 break-all text-xs text-muted">{current.report_path}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted">PDF</div>
            <div className="mt-1 break-all text-xs text-muted">{current.pdf_path || "打开时重新生成"}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted">MD/PDF size</div>
            <div className="mt-1 text-xs text-muted">{formatBytes(current.size_bytes)} / {formatBytes(current.pdf_size_bytes)}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted">Modified</div>
            <div className="mt-1 text-xs text-muted">{formatTime(current.modified_time)}</div>
          </div>
        </div>
      ) : null}

      {error ? <div className="mb-3 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">{error}</div> : null}

      {showPdf && selectedReport ? (
        <div className="overflow-hidden rounded-2xl border border-line bg-black/30">
          <iframe key={`${selectedReport}-${pdfTick}`} title="Package-local PDF preview" src={currentPdfUrl} className="h-[760px] w-full bg-white" />
        </div>
      ) : (
        <pre className="max-h-[760px] overflow-auto rounded-2xl border border-line bg-black/30 p-4 whitespace-pre-wrap font-mono text-xs leading-6 text-muted">
          {content || (loading ? "正在读取报告..." : "还没有本地推理报告。请先在 Pipeline 页面执行 Local Report。")}
        </pre>
      )}
    </Surface>
  );
}
