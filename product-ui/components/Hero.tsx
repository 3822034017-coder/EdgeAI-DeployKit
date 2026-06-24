import { Play, RefreshCcw, UploadCloud } from 'lucide-react';
import { createJob } from '@/lib/api';
import type { ModelItem } from '@/lib/types';

export function Hero({ onRefresh, selectedModel }: { onRefresh: () => void; selectedModel?: ModelItem }) {
  async function runCheck() {
    if (!selectedModel) return;
    await createJob({ action: 'check', params: { model: selectedModel.path } });
    onRefresh();
  }

  return (
    <header id="overview" className="flex items-start justify-between border-b border-line pb-6">
      <div>
        <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.22em] text-cyan/80">
          <span className="status-dot" /> openEuler · ONNX Runtime · Ascend 310B4
        </div>
        <h1 className="mt-4 max-w-4xl text-5xl font-semibold tracking-[-0.055em] text-slate-50">Edge deployment workbench</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
          把模型检查、量化、性能评测、QEMU 验证、香橙派 AIPro 部署与报告矩阵整合成可观测、可恢复、可交付的操作台。
        </p>
      </div>
      <div className="flex gap-3">
        <button className="btn btn-secondary" onClick={onRefresh}><RefreshCcw className="h-4 w-4" />Refresh</button>
        <a className="btn btn-secondary" href="#models"><UploadCloud className="h-4 w-4" />Import ONNX</a>
        <button className="btn btn-primary" onClick={runCheck} disabled={!selectedModel}><Play className="h-4 w-4" />Run check</button>
      </div>
    </header>
  );
}
