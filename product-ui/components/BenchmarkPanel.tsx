import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { MatrixRow } from '@/lib/types';
import { SectionTitle, Surface } from './ui';

function buildData(matrix: MatrixRow[]) {
  const rows = matrix.length ? matrix : [{ model: 'empty', board_latency_ms: 0 } as MatrixRow];
  return rows.map((row, index) => {
    const board = Number(row.board_latency_ms || 0);
    return {
      name: row.model || `model-${index + 1}`,
      board,
      pc: board ? board * 1.35 : 0,
      p95: board ? board * 1.62 : 0,
    };
  });
}

export function BenchmarkPanel({ matrix }: { matrix: MatrixRow[] }) {
  const data = buildData(matrix);

  return (
    <Surface className="p-5">
      <SectionTitle label="Benchmark" title="Latency profile" description="" />
      <div className="h-[314px] rounded-2xl border border-line bg-black/20 p-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 15, right: 12, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id="boardV2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#6EDBD5" stopOpacity={0.24}/><stop offset="95%" stopColor="#6EDBD5" stopOpacity={0}/></linearGradient>
              <linearGradient id="pcV2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#82AFFF" stopOpacity={0.18}/><stop offset="95%" stopColor="#82AFFF" stopOpacity={0}/></linearGradient>
              <linearGradient id="p95V2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#E7BD68" stopOpacity={0.16}/><stop offset="95%" stopColor="#E7BD68" stopOpacity={0}/></linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(148,163,184,.12)" vertical={false} />
            <XAxis dataKey="name" stroke="#8A96A8" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} />
            <YAxis stroke="#8A96A8" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} width={38} />
            <Tooltip contentStyle={{ background: '#0A0E15', border: '1px solid rgba(148,163,184,.16)', borderRadius: 12, color: '#EEF3FA' }} />
            <Area type="monotone" dataKey="p95" name="p95 estimate" stroke="#E7BD68" fill="url(#p95V2)" strokeWidth={1.5} />
            <Area type="monotone" dataKey="pc" name="pc baseline" stroke="#82AFFF" fill="url(#pcV2)" strokeWidth={1.5} />
            <Area type="monotone" dataKey="board" name="board latency" stroke="#6EDBD5" fill="url(#boardV2)" strokeWidth={2.2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Surface>
  );
}
