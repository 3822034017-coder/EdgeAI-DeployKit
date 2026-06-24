import { Cpu, Info, Play } from 'lucide-react';
import { createJob } from '@/lib/api';
import { compactPath, formatSize } from '@/lib/format';
import type { ModelItem } from '@/lib/types';
import { Badge, Card, SectionHeader } from './ui';

export function ModelTable({ models, selectedPath, onSelect, onRefresh }: { models: ModelItem[]; selectedPath?: string; onSelect: (model: ModelItem) => void; onRefresh: () => void }) {
  async function launch(action: string, model: ModelItem) {
    await createJob({ action, params: { model: model.path } });
    onRefresh();
  }

  return (
    <Card id="models" className="p-5">
      <SectionHeader eyebrow="Model registry" title="Models" description="扫描 models、examples、inputs、outputs 中的 ONNX；选择一个模型后可触发 model-info / check / benchmark。" />
      <div className="overflow-hidden rounded-2xl border border-line">
        <div className="grid grid-cols-[1.15fr_1.8fr_.7fr_.7fr_.8fr] gap-3 border-b border-line bg-white/[.025] px-4 py-3 table-head">
          <div>Name</div><div>Path</div><div>Type</div><div>Size</div><div>Actions</div>
        </div>
        <div className="max-h-[360px] overflow-auto scrollbar-thin">
          {models.map((model) => (
            <button key={model.path} onClick={() => onSelect(model)} className={`grid w-full grid-cols-[1.15fr_1.8fr_.7fr_.7fr_.8fr] items-center gap-3 border-b border-line/70 px-4 py-3 text-left transition hover:bg-white/[.026] ${selectedPath === model.path ? 'bg-cyan/[.045]' : ''}`}>
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-line bg-white/[.03]"><Cpu className="h-4 w-4 text-cyan" /></span>
                <div>
                  <div className="text-sm font-medium text-slate-100">{model.name}</div>
                  <div className="text-xs text-muted">{model.source}</div>
                </div>
              </div>
              <div className="font-mono text-xs text-muted">{compactPath(model.path)}</div>
              <div><Badge tone="violet">{model.type}</Badge></div>
              <div className="text-sm text-slate-300">{formatSize(model.size_mb)}</div>
              <div className="flex gap-2" onClick={(event: any) => event.stopPropagation()}>
                <button className="btn btn-secondary !min-h-8 !rounded-lg !px-2" onClick={() => launch('model-info', model)}><Info className="h-3.5 w-3.5" /></button>
                <button className="btn btn-secondary !min-h-8 !rounded-lg !px-2" onClick={() => launch('check', model)}><Play className="h-3.5 w-3.5" /></button>
              </div>
            </button>
          ))}
        </div>
      </div>
    </Card>
  );
}
