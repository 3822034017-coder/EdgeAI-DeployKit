"use client";

import * as React from "react";

export function CollapsibleSection({
  title,
  kicker,
  defaultOpen = false,
  children,
}: {
  title: string;
  kicker?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(defaultOpen);

  return (
    <section className="rounded-[26px] border border-white/10 bg-slate-950/45 p-4">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-4 text-left"
      >
        <div>
          {kicker ? <div className="product-kicker">{kicker}</div> : null}
          <h2 className="mt-1 text-lg font-black text-white">{title}</h2>
        </div>
        <span className="rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-xs font-bold text-slate-200">
          {open ? "收起" : "展开"}
        </span>
      </button>
      {open ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}
