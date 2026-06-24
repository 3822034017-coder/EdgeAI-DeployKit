import { CheckCircle2, FileJson, PackageCheck, Play, RotateCw, ServerCog, ShieldCheck, Zap } from 'lucide-react';
import { compactPath, statusTone } from '@/lib/format';
import type { MatrixRow, ModelItem, Tone } from '@/lib/types';
import { Badge, SectionTitle, Surface } from './ui';

type PipelineAction =
  | 'check'
  | 'quantize'
  | 'benchmark'
  | 'package'
  | 'board-sync'
  | 'board-run'
  | 'board-deploy'
  | 'matrix'
  | 'report'
  | 'html'
  | 'pdf';

const steps = [
  { key: 'check', title: 'Check', desc: 'ONNX checker + graph IO', icon: ShieldCheck, field: 'onnx_check', action: 'check' },
  { key: 'quantize', title: 'Quantize', desc: 'FP32 → INT8 ONNX', icon: RotateCw, field: undefined, action: 'quantize' },
  { key: 'benchmark', title: 'Benchmark', desc: 'PC latency + image result', icon: Zap, field: 'benchmark', action: 'benchmark' },
  { key: 'package', title: 'Package', desc: 'model.json + input.npy', icon: PackageCheck, field: 'package', action: 'package' },
  { key: 'sync', title: 'Board Sync', desc: 'SSH / SCP to AIPro', icon: ServerCog, field: 'board_sync', action: 'board-sync' },
  { key: 'run', title: 'Remote Infer', desc: 'ATC OM + airloader run', icon: Play, field: 'board_run', action: 'board-run' },
  { key: 'report', title: 'Report / PDF', desc: 'matrix → md/html/pdf', icon: FileJson, field: undefined, action: 'report' },
] as const;


function displayStepModelName(model?: ModelItem) {
  if (!model) return "no matrix";
  const parts = model.path.split("/").filter(Boolean);
  const file = parts.at(-1) || model.name;
  const parent = parts.at(-2);

  if (parent && (model.name === "model" || model.name === "model.onnx" || file === "model.onnx")) {
    return parent;
  }

  if (model.name && model.name !== "model" && model.name !== "model.onnx") {
    return model.name.replace(/\.onnx$/i, "");
  }

  return parent || model.type || "model";
}

function matrixForModel(matrix: MatrixRow[], selectedModel?: ModelItem) {
  if (!matrix.length) return undefined;
  if (!selectedModel) return matrix[0];
  return matrix.find((row) => selectedModel.path.includes(String(row.model || ''))) || matrix.find((row) => String(row.model || '').includes(selectedModel.name)) || matrix.find((row) => String(row.model_type || '') === selectedModel.type) || matrix[0];
}

function statusFor(row: MatrixRow | undefined, field?: keyof MatrixRow): { label: string; tone: Tone } {
  if (!field) return { label: 'ready', tone: 'cyan' };
  const label = String(row?.[field] || 'NOT_RUN');
  return { label, tone: statusTone(label) };
}

export function PipelineStepper({
  matrix,
  selectedModel,
  selectedInputPath,
  boardHost,
  onRunAction,
}: {
  matrix: MatrixRow[];
  selectedModel?: ModelItem;
  selectedInputPath?: string;
  selectedInputVersion?: number;
  boardHost?: string;
  onRunAction?: (action: PipelineAction) => void | Promise<void>;
  onRefresh: () => void;
}) {
  const row = matrixForModel(matrix, selectedModel);
  const runAction = onRunAction || (() => undefined);
  const contextLines = [
    selectedModel ? compactPath(selectedModel.path, 96) : 'No ONNX model selected.',
    selectedInputPath ? `input: ${compactPath(selectedInputPath, 96)}` : undefined,
    boardHost ? `host: ${boardHost}` : undefined,
  ].filter(Boolean).join("\n");

  return (
    <Surface className="p-5">
      <SectionTitle
        label="Pipeline"
        title="Deployment flow"
        description="按真实 edgeai 命令顺序执行：检查、量化、Benchmark、打包、上传、远程推理、报告和 PDF。"
        right={<Badge tone="neutral">{row?.model || displayStepModelName(selectedModel)}</Badge>}
      />

      <div className="grid grid-cols-7 gap-2">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const status = statusFor(row, step.field as keyof MatrixRow | undefined);
          return (
            <button key={step.key} type="button" onClick={() => void runAction(step.action)} className="group relative min-h-[148px] rounded-2xl border border-line bg-white/[0.025] p-3 text-left transition hover:border-cyan/25 hover:bg-white/[0.04]">
              {index < steps.length - 1 ? <span className="absolute right-[-8px] top-10 z-10 h-px w-4 bg-line" /> : null}
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-muted">0{index + 1}</span>
                <Badge tone={status.tone}>{status.label}</Badge>
              </div>
              <div className="mt-4 flex h-9 w-9 items-center justify-center rounded-xl border border-line bg-black/20 text-cyan">
                <Icon className="h-4 w-4" />
              </div>
              <div className="mt-4 text-sm font-semibold text-ink">{step.title}</div>
              <div className="mt-2 text-xs leading-5 text-muted">{step.desc}</div>
            </button>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-[1fr_auto_auto] gap-3 rounded-2xl border border-line bg-black/20 p-4">
        <div>
          <div className="label">Selected command context</div>
          <div className="mt-2 font-mono text-xs leading-5 text-muted">
            {contextLines}
          </div>
        </div>
        <button className="btn" onClick={() => void runAction('board-deploy')} disabled={!selectedModel}>
          <Play className="h-4 w-4" /> One-click deploy
        </button>
        <button className="btn btn-primary" onClick={() => void runAction('check')} disabled={!selectedModel}>
          <CheckCircle2 className="h-4 w-4" /> Run check
        </button>
      </div>
    </Surface>
  );
}
