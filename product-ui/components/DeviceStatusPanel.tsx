import { Box, Cpu, HardDrive, Server, ShieldAlert } from 'lucide-react';
import type { HealthResponse, Job } from '@/lib/types';
import { jobTone } from '@/lib/format';
import { Badge, SectionTitle, Surface } from './ui';

function available(health: HealthResponse, key: string) {
  return health.checks.some((item) => item.name.toLowerCase().includes(key.toLowerCase()) && item.available);
}

export function DeviceStatusPanel({ health, jobs }: { health: HealthResponse; jobs: Job[] }) {
  const latest = jobs[0];
  const devices = [
    { name: 'OrangePi AIPro', detail: available(health, 'atc') ? 'ATC available' : 'ATC missing / board flow limited', icon: Cpu, ok: available(health, 'atc') },
    { name: 'QEMU ARM64', detail: available(health, 'qemu') ? 'qemu-system-aarch64 ready' : 'QEMU missing', icon: Server, ok: available(health, 'qemu') },
    { name: 'Docker delivery', detail: available(health, 'docker') ? 'docker CLI ready' : 'Docker missing', icon: HardDrive, ok: available(health, 'docker') },
  ];

  return (
    <Surface id="board" className="p-5">
      <SectionTitle label="Runtime" title="Board & session" description="更偏工作台：显示当前设备能力、最近任务和缺失项。" />
      <div className="space-y-3">
        {devices.map(({ name, detail, icon: Icon, ok }) => (
          <div key={name} className="surface-flat p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-black/20"><Icon className="h-4 w-4 text-cyan" /></span>
                <div><div className="text-sm font-semibold text-ink">{name}</div><div className="text-xs text-muted">{detail}</div></div>
              </div>
              <Badge tone={ok ? 'green' : 'amber'}>{ok ? 'ready' : 'limited'}</Badge>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-2xl border border-line bg-black/20 p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink"><Box className="h-4 w-4 text-cyan" /> Active session</div>
          <Badge tone={latest ? jobTone(latest.status) : 'neutral'}>{latest?.status || 'idle'}</Badge>
        </div>
        <div className="mt-3 space-y-2 text-xs leading-5 text-muted">
          <div className="flex items-center justify-between"><span>Last action</span><span className="font-mono text-slate-300">{latest?.action || '-'}</span></div>
          <div className="flex items-center justify-between"><span>Job id</span><span className="font-mono text-slate-300">{latest?.id || '-'}</span></div>
        </div>
      </div>

      {!available(health, 'atc') ? (
        <div className="mt-4 flex gap-3 rounded-2xl border border-amber/20 bg-amber/10 p-4 text-xs leading-5 text-amber">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" /> ATC 缺失时可以跑 PC 侧 check / benchmark / report，但板端 OM 转换会受限。
        </div>
      ) : null}
    </Surface>
  );
}
