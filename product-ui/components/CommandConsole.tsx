import { TerminalSquare } from 'lucide-react';
import { fetchJobLogs } from '@/lib/api';
import { compactPath, jobTone } from '@/lib/format';
import type { Job } from '@/lib/types';
import { Badge, Card, SectionHeader } from './ui';
import { useEffect, useState } from 'react';

export function CommandConsole({ jobs }: { jobs: Job[] }) {
  const [active, setActive] = useState<Job | undefined>(jobs[0]);
  const [logs, setLogs] = useState('');

  useEffect(() => {
    const next = jobs[0];
    setActive(next);
  }, [jobs]);

  useEffect(() => {
    let mounted = true;
    if (!active?.id) {
      setLogs('');
      return;
    }
    fetchJobLogs(active.id).then((text) => {
      if (mounted) setLogs(text);
    });
    return () => { mounted = false; };
  }, [active]);

  return (
    <Card id="runtime" className="p-5">
      <SectionHeader title="Command console" description="后端所有任务都落到 outputs/jobs/<job_id>，刷新页面后仍可恢复状态。" right={<TerminalSquare className="h-5 w-5 text-muted" />} />
      <div className="grid grid-cols-[.85fr_1.15fr] gap-4">
        <div className="space-y-2">
          {jobs.slice(0, 8).map((job) => (
            <button key={job.id} onClick={() => setActive(job)} className={`w-full rounded-2xl border border-line px-4 py-3 text-left transition hover:bg-white/[.035] ${active?.id === job.id ? 'bg-cyan/[.045]' : 'bg-white/[.022]'}`}>
              <div className="flex items-center justify-between"><span className="text-sm font-semibold text-slate-100">{job.action}</span><Badge tone={jobTone(job.status)}>{job.status}</Badge></div>
              <div className="mt-2 font-mono text-[11px] leading-5 text-muted">{compactPath(job.command.join(' '), 70)}</div>
            </button>
          ))}
        </div>
        <pre className="console scrollbar-thin min-h-[290px] overflow-auto rounded-2xl p-4 text-xs leading-6">{logs || active?.command?.join(' ') || 'No job selected.'}</pre>
      </div>
    </Card>
  );
}
