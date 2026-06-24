import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function backendBase() {
  return process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const packageName = searchParams.get("package_name") || "";
  const force = searchParams.get("force") || "0";
  const q = new URLSearchParams({ package_name: packageName, force });
  const upstream = `${backendBase()}/api/local-task-result?${q.toString()}`;
  const resp = await fetch(upstream, { cache: "no-store" });
  const text = await resp.text();
  return new NextResponse(text, {
    status: resp.status,
    headers: {
      "content-type": resp.headers.get("content-type") || "application/json; charset=utf-8",
      "cache-control": "no-store, no-cache, must-revalidate, max-age=0",
    },
  });
}
