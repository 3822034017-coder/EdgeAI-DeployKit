import { Archive, Cpu, PlayCircle } from 'lucide-react';
import { countPass, formatSize, jobTone } from '@/lib/format';
import type { DashboardData, ModelItem } from '@/lib/types';
import { Badge, StatLine, Surface } from './ui';

export function WorkspaceSummary({ data, selectedModel }: { data: DashboardData; selectedModel?: ModelItem }) {
  const latestJob = data.jobs[0];
  const boardPassed = countPass(data.matrix, 'board_run');
  const packages = data.artifacts.filter((item) => item.kind === 'package').length;
  const reports = data.artifacts.filter((item) => item.kind === 'report' || item.kind === 'matrix').length;

  return (
    <section id="overview" className="grid grid-cols-[1.12fr_.88fr_.88fr_.88fr] gap-4">
      <Surface className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="label">Current model</div>
            <div className="mt-3 text-xl font-semibold tracking-[-0.025em] text-ink">{selectedModel?.name || 'No model selected'}</div>
            <div className="mt-2 font-mono text-xs leading-5 text-muted">{selectedModel?.path || 'Select an ONNX model from registry.'}</div>
          </div>
          <Badge tone={selectedModel ? 'cyan' : 'amber'}>{selectedModel?.type || 'empty'}</Badge>
        </div>
        <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
          <div className="surface-subtle p-3"><div className="text-muted">Size</div><div className="mt-1 font-semibold text-ink">{formatSize(selectedModel?.size_mb)}</div></div>
          <div className="surface-subtle p-3"><div className="text-muted">Source</div><div className="mt-1 font-semibold text-ink">{selectedModel?.source || '-'}</div></div>
          <div className="surface-subtle p-3"><div className="text-muted">Models</div><div className="mt-1 font-semibold text-ink">{data.models.length}</div></div>
        </div>
      </Surface>

      <Surface className="p-5">
        <div className="mb-4 flex items-center justify-between"><PlayCircle className="h-4 w-4 text-cyan" /><Badge tone={latestJob ? jobTone(latestJob.status) : 'neutral'}>{latestJob?.status || 'idle'}</Badge></div>
        <StatLine label="Active run" value={latestJob?.action || 'No job'} hint={latestJob ? latestJob.id : 'Start a check or benchmark job.'} />
      </Surface>

      <Surface className="p-5">
        <div className="mb-4 flex items-center justify-between"><Cpu className="h-4 w-4 text-cyan" /><Badge tone={boardPassed ? 'green' : 'amber'}>{boardPassed}/{data.matrix.length || 0}</Badge></div>
        <StatLine label="Board passed" value={`${boardPassed}/${data.matrix.length || 0}`} hint="Board Run PASS from matrix.json" />
      </Surface>

      <Surface className="p-5">
        <div className="mb-4 flex items-center justify-between"><Archive className="h-4 w-4 text-cyan" /><Badge tone="neutral">outputs</Badge></div>
        <div className="grid grid-cols-2 gap-4">
          <StatLine label="Packages" value={packages} hint="deploy artifacts" />
          <StatLine label="Reports" value={reports} hint="matrix / html / pdf" />
        </div>
      </Surface>
    </section>
  );
}
