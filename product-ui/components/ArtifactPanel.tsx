import { FileText } from 'lucide-react';
import { compactPath, formatSize } from '@/lib/format';
import type { ArtifactItem } from '@/lib/types';
import { Badge, Card, SectionHeader } from './ui';

export function ArtifactPanel({ artifacts }: { artifacts: ArtifactItem[] }) {
  return (
    <Card id="reports" className="p-5">
      <SectionHeader title="Reports & artifacts" description="统一展示 reports、outputs/model_matrix、outputs/packages、benchmark JSON。" />
      <div className="space-y-2">
        {artifacts.slice(0, 10).map((item) => (
          <div key={item.path} className="flex items-center justify-between rounded-2xl border border-line bg-white/[.025] px-4 py-3">
            <div className="flex items-center gap-3">
              <FileText className="h-4 w-4 text-cyan" />
              <div><div className="text-sm text-slate-100">{item.name}</div><div className="font-mono text-xs text-muted">{compactPath(item.path)}</div></div>
            </div>
            <div className="flex items-center gap-3"><Badge tone="neutral">{item.kind}</Badge><span className="text-xs text-muted">{formatSize(item.size_mb)}</span></div>
          </div>
        ))}
      </div>
    </Card>
  );
}
