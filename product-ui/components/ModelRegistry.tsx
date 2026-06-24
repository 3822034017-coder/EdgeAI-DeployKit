"use client";

import { useState } from "react";
import { Cpu, Info, Play, Zap } from "lucide-react";
import { createJob } from "@/lib/api";
import { compactPath, formatSize } from "@/lib/format";
import type { ModelItem } from "@/lib/types";
import { Badge, SectionTitle, Surface } from "./ui";

type RegistryAction = "check" | "benchmark";

function displayName(model: ModelItem) {
  const parts = model.path.split("/").filter(Boolean);
  const file = parts.at(-1) || model.name;
  const parent = parts.at(-2);

  if ((model.name === "model" || model.name === file.replace(".onnx", "")) && parent) {
    return parent;
  }

  return model.name || parent || file || "model";
}

export function ModelRegistry({
  models,
  selectedPath,
  onSelect,
  onRefresh,
  onOpenRuntime,
  onOpenBenchmark,
}: {
  models: ModelItem[];
  selectedPath?: string;
  onSelect: (model: ModelItem) => void;
  onRefresh: () => void | Promise<void>;
  onOpenRuntime?: () => void;
  onOpenBenchmark?: () => void;
}) {
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [infoModel, setInfoModel] = useState<ModelItem | null>(null);

  function showInfo(model: ModelItem) {
    onSelect(model);
    setInfoModel(model);
  }

  async function launch(action: RegistryAction, model: ModelItem) {
    const key = `${action}:${model.path}`;

    try {
      setBusyKey(key);
      onSelect(model);

      await createJob({
        action,
        params: {
          model: model.path,
        },
      });

      await onRefresh();

      if (action === "check") {
        onOpenRuntime?.();
      }

      if (action === "benchmark") {
        onOpenBenchmark?.();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      window.alert(`任务创建失败：${action}\n${message}`);
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <Surface id="models" className="p-5 model-registry-surface">
      <SectionTitle
        label="Registry"
        title="Model registry"
        description="从 models / examples / inputs / outputs 扫描 ONNX，右侧动作可直接创建工程任务。"
      />

      <div className="overflow-hidden rounded-2xl border border-line">
        <div className="grid grid-cols-[1.1fr_1.8fr_.55fr_.55fr_.7fr] gap-3 border-b border-line bg-white/[0.025] px-4 py-3 table-head">
          <div>Name</div>
          <div>Path</div>
          <div>Type</div>
          <div>Size</div>
          <div>Actions</div>
        </div>

        <div className="fine-scrollbar max-h-[390px] overflow-auto">
          {models.map((model) => {
            const checkBusy = busyKey === `check:${model.path}`;
            const benchmarkBusy = busyKey === `benchmark:${model.path}`;
            const rowBusy = checkBusy || benchmarkBusy;

            return (
              <div
                key={model.path}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(model)}
                onKeyDown={(event: any) => {
                  if (event.key === "Enter") {
                    onSelect(model);
                  }
                }}
                className={`grid w-full cursor-pointer grid-cols-[1.1fr_1.8fr_.55fr_.55fr_.7fr] items-center gap-3 border-b border-line/60 px-4 py-3 text-left transition hover:bg-white/[0.028] ${
                  selectedPath === model.path ? "bg-cyan/[0.045]" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-line bg-black/20">
                    <Cpu className="h-4 w-4 text-cyan" />
                  </span>

                  <div>
                    <div className="text-sm font-medium text-ink">{displayName(model)}</div>
                    <div className="text-xs text-muted">{model.source}</div>
                  </div>
                </div>

                <div className="font-mono text-xs text-muted">
                  {compactPath(model.path, 68)}
                </div>

                <div>
                  <Badge tone="violet">{model.type}</Badge>
                </div>

                <div className="text-xs text-slate-300">{formatSize(model.size_mb)}</div>

                <div
                  className="flex gap-2"
                  onClick={(event: any) => event.stopPropagation()}
                >
                  <button
                    type="button"
                    className="btn !min-h-8 !rounded-lg !px-2"
                    onClick={() => showInfo(model)}
                    disabled={rowBusy}
                    title="查看模型信息"
                  >
                    <Info className="h-3.5 w-3.5" />
                  </button>

                  <button
                    type="button"
                    className="btn !min-h-8 !rounded-lg !px-2"
                    onClick={() => void launch("check", model)}
                    disabled={rowBusy}
                    title="执行 check，跳转 Runtime 查看日志"
                  >
                    <Play className="h-3.5 w-3.5" />
                  </button>

                  <button
                    type="button"
                    className="btn !min-h-8 !rounded-lg !px-2"
                    onClick={() => void launch("benchmark", model)}
                    disabled={rowBusy}
                    title="执行 benchmark，跳转 Benchmark 页面"
                  >
                    <Zap className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {infoModel ? (
        <div className="model-info-popover" role="dialog" aria-modal="true">
          <div className="model-info-card">
            <div className="model-info-card-head">
              <div>
                <span>Model details</span>
                <h3>{displayName(infoModel)}</h3>
              </div>

              <button
                type="button"
                className="model-info-close"
                onClick={() => setInfoModel(null)}
                aria-label="关闭模型信息"
              >
                <span aria-hidden="true">×</span>
              </button>
            </div>

            <div className="model-info-grid">
              <div>
                <span>Name</span>
                <strong>{displayName(infoModel)}</strong>
              </div>

              <div>
                <span>Type</span>
                <strong>{infoModel.type}</strong>
              </div>

              <div>
                <span>Size</span>
                <strong>{formatSize(infoModel.size_mb)}</strong>
              </div>

              <div>
                <span>Source</span>
                <strong>{infoModel.source}</strong>
              </div>
            </div>

            <div className="model-info-path">
              <span>Path</span>
              <code>{infoModel.path}</code>
            </div>

            <div className="model-info-actions">
              <button
                type="button"
                onClick={() => {
                  setInfoModel(null);
                  void launch("check", infoModel);
                }}
              >
                Run Check
              </button>

              <button
                type="button"
                onClick={() => {
                  setInfoModel(null);
                  void launch("benchmark", infoModel);
                }}
              >
                Benchmark
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </Surface>
  );
}
