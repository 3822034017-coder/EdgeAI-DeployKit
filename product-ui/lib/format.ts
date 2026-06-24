import type { JobStatus, MatrixRow, Tone } from './types';

export function statusTone(status?: string | null): Tone {
  const value = String(status || 'NOT_RUN').toUpperCase();
  if (['PASS', 'SUCCESS', 'OK', 'DONE'].includes(value)) return 'green';
  if (['RUNNING', 'STARTED', 'DEPLOYING'].includes(value)) return 'cyan';
  if (['SKIP', 'SKIPPED', 'PENDING', 'QUEUED', 'NOT_RUN'].includes(value)) return 'amber';
  if (['FAIL', 'FAILED', 'ERROR', 'TIMEOUT'].includes(value)) return 'red';
  return 'neutral';
}

export function jobTone(status: JobStatus): Tone {
  if (status === 'success') return 'green';
  if (status === 'running') return 'cyan';
  if (status === 'queued') return 'amber';
  if (status === 'failed' || status === 'timeout' || status === 'cancelled') return 'red';
  return 'neutral';
}

export function compactPath(path: string, max = 52): string {
  if (path.length <= max) return path;
  const head = path.slice(0, 18);
  const tail = path.slice(path.length - max + 21);
  return `${head}...${tail}`;
}

export function countPass(matrix: MatrixRow[], key: keyof MatrixRow): number {
  return matrix.filter((row) => String(row[key] || '').toUpperCase() === 'PASS').length;
}

export function formatSize(sizeMb?: number): string {
  if (sizeMb === undefined || Number.isNaN(sizeMb)) return '-';
  if (sizeMb < 1) return `${(sizeMb * 1024).toFixed(0)} KB`;
  return `${sizeMb.toFixed(2)} MB`;
}
