import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function backendBase() {
  const base = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
  return base.replace(/\/$/, "");
}

export async function GET(request: NextRequest) {
  const incoming = request.nextUrl.searchParams;
  const mode = incoming.get("mode") || "local";
  const packageName = incoming.get("package_name") || "";
  const t = incoming.get("t") || String(Date.now());

  const q = new URLSearchParams({ mode, force: "1", t });
  if (packageName) q.set("package_name", packageName);

  const upstreamUrl = `${backendBase()}/api/current-run-report-v4/pdf?${q.toString()}`;
  const upstream = await fetch(upstreamUrl, { cache: "no-store" });

  if (!upstream.ok) {
    const text = await upstream.text().catch(() => "");
    return new Response(text || `PDF upstream error: ${upstream.status}`, {
      status: upstream.status,
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "cache-control": "no-store, no-cache, must-revalidate, max-age=0",
        "x-edgeai-pdf-proxy": "v1",
        "x-edgeai-upstream-url": upstreamUrl,
      },
    });
  }

  const body = await upstream.arrayBuffer();
  const headers = new Headers();
  headers.set("content-type", "application/pdf");
  headers.set("content-disposition", `inline; filename="${packageName || mode}_current_run_report.pdf"`);
  headers.set("cache-control", "no-store, no-cache, must-revalidate, max-age=0");
  headers.set("pragma", "no-cache");
  headers.set("expires", "0");
  headers.set("x-edgeai-pdf-proxy", "v1");
  headers.set("x-edgeai-report-mode", mode);
  headers.set("x-edgeai-report-name", packageName || mode);
  const upstreamPath = upstream.headers.get("x-edgeai-report-pdf-path");
  if (upstreamPath) headers.set("x-edgeai-report-pdf-path", upstreamPath);

  return new Response(body, { status: 200, headers });
}
