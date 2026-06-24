import { Cpu, HardDrive, Server } from 'lucide-react';
import { Badge, Card, SectionHeader } from './ui';
import type { HealthResponse } from '@/lib/types';

export function DevicePanel({ health }: { health: HealthResponse }) {
  const items = [
    { name: 'OrangePi AIPro', detail: 'SSH / ATC / airloader target', icon: Cpu, tone: 'green' as const },
    { name: 'QEMU ARM64', detail: 'kernel + initramfs + aarch64 runtime', icon: Server, tone: 'amber' as const },
    { name: 'Docker delivery', detail: 'docker build / run validation', icon: HardDrive, tone: 'violet' as const },
  ];

  return (
    <Card id="board" className="p-5">
      <SectionHeader title="Board & runtime" description="展示板端和本机工具链状态。真实连板参数通过后端 job 提交，前端不保存密码。" />
      <div className="space-y-3">
        {items.map(({ name, detail, icon: Icon, tone }) => (
          <div key={name} className="subtle-card rounded-2xl p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-white/[.03]"><Icon className="h-4 w-4 text-cyan" /></span>
                <div><div className="text-sm font-semibold text-slate-100">{name}</div><div className="text-xs text-muted">{detail}</div></div>
              </div>
              <Badge tone={tone}>ready</Badge>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 rounded-2xl border border-line bg-black/20 p-4">
        <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-muted">Runtime checks</div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {health.checks.map((item) => <div key={item.name} className="flex items-center justify-between rounded-xl bg-white/[.025] px-3 py-2 text-xs"><span className="text-slate-300">{item.name}</span><Badge tone={item.available ? 'green' : 'red'}>{item.available ? 'ok' : 'miss'}</Badge></div>)}
        </div>
      </div>
    </Card>
  );
}
