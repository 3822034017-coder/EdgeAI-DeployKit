"use client";

import { API_BASE } from "@/lib/api";
import type { ArtifactItem } from "@/lib/types";

function fileUrl(path: string) {
  const cleaned = path.replace(/^\/+/, "");
  const encoded = cleaned.split("/").map((part) => encodeURIComponent(part)).join("/");
  return `${API_BASE}/api/files/${encoded}`;
}

function currentPackageAssets(packageName?: string): ArtifactItem[] {
  if (!packageName || packageName === "model") return [];
  const base = `outputs/packages/${packageName}`;
  return [
    { name: "report.md", path: `${base}/report.md`, kind: "report", size_mb: 0, modified_at: "current" },
    { name: "report.pdf", path: `${base}/report.pdf`, kind: "report", size_mb: 0, modified_at: "current" },
    { name: "model_task.json", path: `${base}/model_task.json`, kind: "other", size_mb: 0, modified_at: "current" },
    { name: "task_result.json", path: `${base}/task_result.json`, kind: "other", size_mb: 0, modified_at: "current" },
    { name: "local_result.json", path: `${base}/local_result.json`, kind: "other", size_mb: 0, modified_at: "current" },
    { name: "compatibility_report.md", path: `${base}/compatibility_report.md`, kind: "other", size_mb: 0, modified_at: "current" },
  ];
}

function isPreviewable(path: string) {
  return /\.(md|pdf|json|png|jpg|jpeg|webp)$/i.test(path);
}

export function CompactReportAssets({
  artifacts = [],
  packageName,
}: {
  artifacts?: ArtifactItem[];
  packageName?: string;
}) {
  const merged = [...currentPackageAssets(packageName), ...(artifacts || [])]
    .filter((item, idx, arr) => item.path && arr.findIndex((x) => x.path === item.path) === idx)
    .slice(0, 18);

  return (
    <section className="rounded-[26px] border border-white/10 bg-slate-950/45 p-4">
      <details>
        <summary className="cursor-pointer list-none">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="product-kicker">Report assets</div>
              <h2 className="mt-1 text-lg font-black text-white">紧凑报告资产</h2>
              <p className="mt-1 text-sm text-slate-400">默认折叠。展开后可浏览器预览或下载，不再用大列表占满页面。</p>
            </div>
            <span className="rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-xs font-bold text-slate-200">展开 / 收起</span>
          </div>
        </summary>

        <div className="mt-4 grid gap-2">
          {merged.map((item) => {
            const url = fileUrl(item.path);
            return (
              <div key={item.path} className="grid gap-2 rounded-2xl border border-white/10 bg-black/20 p-3 text-xs text-slate-300 md:grid-cols-[1fr_auto] md:items-center">
                <div className="min-w-0">
                  <div className="font-bold text-white">{item.name || item.path.split("/").pop()}</div>
                  <div className="mt-1 truncate font-mono text-slate-500">{item.path}</div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {isPreviewable(item.path) ? (
                    <a href={url} target="_blank" rel="noreferrer" className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 font-bold text-cyan-100">
                      浏览器预览
                    </a>
                  ) : null}
                  <a href={url} download className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-bold text-slate-200">
                    下载
                  </a>
                </div>
              </div>
            );
          })}
          {merged.length === 0 ? <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-400">暂无报告资产。</div> : null}
        </div>
      </details>
    </section>
  );
}
