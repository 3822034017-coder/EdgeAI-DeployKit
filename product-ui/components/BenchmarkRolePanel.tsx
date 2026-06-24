"use client";

export function BenchmarkRolePanel() {
  return (
    <section className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
      <div className="product-kicker">Performance Lab</div>
      <h2 className="mt-2 text-2xl font-black text-white">Benchmark 的新定位</h2>
      <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-300">
        Benchmark 不再作为主部署流程入口。它的作用是：当本地模型已经转换并跑通后，用于查看 latency、p50 / p95、内存、运行环境差异，辅助用户判断模型是否适合在 Windows / macOS / Linux x86 / Linux ARM 的本地软件包中使用。
      </p>
    </section>
  );
}
