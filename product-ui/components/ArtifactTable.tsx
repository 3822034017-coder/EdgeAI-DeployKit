import { FileText } from 'lucide-react';
import { compactPath, formatSize } from '@/lib/format';
import type { ArtifactItem } from '@/lib/types';
import { Badge, SectionTitle, Surface } from './ui';

export function ArtifactTable({ artifacts }: { artifacts: ArtifactItem[] }) {
  return (
    <Surface id="reports" className="p-5">
      <SectionTitle label="Artifacts" title="Reports & packages" description="把产物变成可读资产列表，后续可扩展下载/预览按钮。" />
      <div className="space-y-2">
        {artifacts.slice(0, 12).map((item) => (
          <div key={item.path} className="surface-subtle flex items-center justify-between gap-3 px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileText className="h-4 w-4 shrink-0 text-cyan" />
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-ink">{item.name}</div>
                <div className="truncate font-mono text-[11px] text-muted">{compactPath(item.path, 54)}</div>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge tone="neutral">{item.kind}</Badge>
              <span className="text-xs text-muted">{formatSize(item.size_mb)}</span>
            </div>
          </div>
        ))}
        {!artifacts.length ? <div className="rounded-2xl border border-line py-10 text-center text-sm text-muted">No artifacts found.</div> : null}
      </div>
    </Surface>
  );
}
