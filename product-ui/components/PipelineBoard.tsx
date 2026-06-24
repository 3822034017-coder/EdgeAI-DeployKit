import { Badge, Card, SectionHeader } from './ui';
import { statusTone } from '@/lib/format';
import type { MatrixRow } from '@/lib/types';

const stages = [
  { id: '01', key: 'model', title: 'Model Intake', text: 'ONNX / image / JSON contract' },
  { id: '02', key: 'benchmark', title: 'Benchmark', text: 'avg / p50 / p95 / memory' },
  { id: '03', key: 'package', title: 'Package', text: 'model.json + input.npy' },
  { id: '04', key: 'board_sync', title: 'Board Sync', text: 'SSH / SCP to AIPro' },
  { id: '05', key: 'om_convert', title: 'ATC Convert', text: 'ONNX → OM' },
  { id: '06', key: 'board_run', title: 'NPU Run', text: 'airloader inference' },
] as const;

export function PipelineBoard({ matrix }: { matrix: MatrixRow[] }) {
  const row = matrix[0] || {};

  return (
    <Card id="pipeline" className="p-5">
      <SectionHeader title="Deployment pipeline" description="把原来的离散按钮整理成可观察的状态流。默认展示 matrix.json 中第一条模型记录，后端接入后可切换 session/job。" right={<Badge tone="violet">matrix view</Badge>} />
      <div className="grid grid-cols-6 gap-3">
        {stages.map((stage) => {
          const status = stage.key === 'model' ? (row.model ? 'PASS' : 'NOT_RUN') : String(row[stage.key] || 'NOT_RUN');
          return (
            <div key={stage.id} className="subtle-card min-h-[158px] rounded-[22px] p-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-muted">{stage.id}</span>
                <Badge tone={statusTone(status)}>{status}</Badge>
              </div>
              <div className="mt-6 text-sm font-semibold text-slate-100">{stage.title}</div>
              <div className="mt-2 text-xs leading-5 text-muted">{stage.text}</div>
              <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-slate-800/80">
                <div className={`h-full rounded-full ${statusTone(status) === 'green' ? 'bg-green' : statusTone(status) === 'red' ? 'bg-red' : 'bg-slate-700'}`} style={{ width: statusTone(status) === 'green' ? '100%' : '32%' }} />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
