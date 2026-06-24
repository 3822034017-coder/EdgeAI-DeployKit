import clsx from 'clsx';
import type { Tone } from '@/lib/types';

export function Surface({ id, className, children }: { id?: string; className?: string; children?: React.ReactNode }) {
  return <section id={id} className={clsx('surface', className)}>{children}</section>;
}

// Backward-compatible alias: old components may still import Card.
export function Card({ id, className, children }: { id?: string; className?: string; children?: React.ReactNode }) {
  return <Surface id={id} className={className}>{children}</Surface>;
}

export function Badge({ children, tone = 'neutral' }: { children?: React.ReactNode; tone?: Tone }) {
  return <span className={clsx('badge', `badge-${tone}`)}>{children}</span>;
}

export function SectionTitle({
  label,
  title,
  description,
  right,
}: {
  label?: string;
  title: string;
  description?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        {label ? <div className="label mb-2">{label}</div> : null}
        <h2 className="text-base font-semibold tracking-[-0.01em] text-ink">{title}</h2>
        {description ? <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">{description}</p> : null}
      </div>
      {right}
    </div>
  );
}

// Backward-compatible alias: old components may still import SectionHeader.
export function SectionHeader({
  eyebrow,
  title,
  description,
  right,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  right?: React.ReactNode;
}) {
  return <SectionTitle label={eyebrow} title={title} description={description} right={right} />;
}

export function StatLine({ label, value, hint }: { label: string; value: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-ink">{value}</div>
      {hint ? <div className="mt-1 text-xs leading-5 text-muted">{hint}</div> : null}
    </div>
  );
}

// Backward-compatible alias: old KpiGrid may still import Metric.
export function Metric({ label, value, hint, tone = 'neutral' }: { label: string; value: string; hint: string; tone?: Tone }) {
  return (
    <Surface className="p-5">
      <div className="flex items-center justify-between gap-4">
        <div className="label">{label}</div>
        <Badge tone={tone}>{tone}</Badge>
      </div>
      <div className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-ink">{value}</div>
      <div className="mt-2 text-sm leading-6 text-muted">{hint}</div>
    </Surface>
  );
}
