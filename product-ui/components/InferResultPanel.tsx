"use client";

import { fileUrl } from "@/lib/api";
import { compactPath } from "@/lib/format";
import type { InferDetection, InferResult, ModelItem } from "@/lib/types";

type ActionName =
  | "check"
  | "quantize"
  | "benchmark"
  | "package"
  | "board-sync"
  | "board-run"
  | "board-deploy"
  | "matrix"
  | "report"
  | "html"
  | "pdf";

function displayModelName(model?: ModelItem) {
  if (!model) return "model";
  const parts = model.path.split("/").filter(Boolean);
  const file = parts.at(-1) || model.name || "model.onnx";
  const parent = parts.at(-2);
  if (parent && (model.name === "model" || model.name === "model.onnx" || file === "model.onnx")) return parent;
  return (model.name || parent || file).replace(/\.onnx$/i, "");
}

export function findInferResult(results: InferResult[], model?: ModelItem) {
  if (!results.length) return undefined;
  if (!model) return results[0];

  const display = displayModelName(model).toLowerCase();
  const parts = model.path.split("/").filter(Boolean);
  const parent = String(parts.at(-2) || "").toLowerCase();
  const base = display.includes("yolov5n") ? "yolov5n" : display;

  return (
    results.find((item) => item.model.toLowerCase() === display) ||
    results.find((item) => item.model.toLowerCase() === parent) ||
    results.find((item) => item.model.toLowerCase().includes(display)) ||
    results.find((item) => item.model.toLowerCase().includes(parent)) ||
    results.find((item) => String(item.model_type || "").toLowerCase().includes(display)) ||
    results.find((item) => String(item.model_type || "").toLowerCase().includes(base)) ||
    results[0]
  );
}

function percent(value?: number | string | null) {
  if (value === undefined || value === null || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (number <= 1) return `${(number * 100).toFixed(2)}%`;
  return `${number.toFixed(2)}%`;
}

function ms(value?: number | string | null) {
  if (value === undefined || value === null || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(3)} ms` : String(value);
}

function bboxText(item: InferDetection) {
  if (!item.bbox?.length) return "—";
  return item.bbox.map((value) => String(value)).join(", ");
}

function actionNeedsInput(action: ActionName) {
  return action === "benchmark" || action === "package" || action === "board-sync" || action === "board-run" || action === "board-deploy";
}

function actionNeedsHost(action: ActionName) {
  return action === "board-sync" || action === "board-run" || action === "board-deploy";
}

function top5Label(item: Record<string, unknown>) {
  return String(item.label_zh || item.label_en || item.label || item.index || item.class_id || "—");
}

function top5SubLabel(item: Record<string, unknown>) {
  const label = item.label_en || item.label;
  const cls = item.index || item.class_id;
  if (label && cls !== undefined && cls !== null) return `#${cls} · ${label}`;
  if (cls !== undefined && cls !== null) return `#${cls}`;
  return "";
}

export function InferResultPanel({
  results,
  selectedModel,
  selectedInputPath,
  selectedInputVersion,
  boardHost,
  running,
  onBoardHostChange,
  onUploadInput,
  onRunAction,
  onOpenRuntime,
  onOpenReports,
}: {
  results: InferResult[];
  selectedModel?: ModelItem;
  selectedInputPath?: string;
  selectedInputVersion?: number;
  boardHost: string;
  running?: boolean;
  onBoardHostChange: (value: string) => void;
  onUploadInput: (file: File) => void | Promise<void>;
  onRunAction: (action: ActionName) => void | Promise<void>;
  onOpenRuntime: () => void;
  onOpenReports: () => void;
}) {
  const result = findInferResult(results, selectedModel);
  const title = displayModelName(selectedModel);
  const isDetection = result?.result_type === "detection";
  const inputImage = selectedInputPath || result?.input_image;
  const resultImage = result?.result_image;
  const prediction = result?.prediction;
  const detections = result?.detections || [];
  const hasInput = Boolean(inputImage);
  const hasHost = Boolean(boardHost.trim());
  const cacheKey = String(selectedInputVersion || result?.updated_at || Date.now());

  const resultMatchesSelectedInput = !selectedInputPath || result?.source_input_path === selectedInputPath;
  const outputNeedsRefresh = Boolean(selectedInputPath && !resultMatchesSelectedInput);

  function disabledFor(action: ActionName) {
    if (running || !selectedModel) return true;
    if (actionNeedsInput(action) && !hasInput) return true;
    if (actionNeedsHost(action) && !hasHost) return true;
    return false;
  }

  return (
    <section className="infer-result-panel">
      <div className="infer-warning-card">
        <strong>板端命令说明</strong>
        <span>
          Windows 浏览器选择的图片会通过后端上传到 Linux 虚拟机的 inputs/images 目录。请先 Package，再 Board Sync / Remote Infer。若刚换了测试图片，旧结果会暂时隐藏，避免把上一次推理图片误当成本次结果。
        </span>
      </div>

      <div className="infer-hero-card">
        <div>
          <div className="product-kicker">Infer Result</div>
          <h2>Board inference workspace</h2>
          <p>
            先上传测试图片，再按完整 EdgeAI 命令链完成检查、量化、打包、上传、ATC 转 OM、板端推理和报告导出。
          </p>
        </div>

        <div className="infer-context-grid">
          <label>
            <span>Board host</span>
            <input
              type="text"
              value={boardHost}
              onChange={(event) => onBoardHostChange(event.target.value)}
              placeholder="192.168.0.36"
            />
          </label>

          <label className="infer-upload-box">
            <span>Test image</span>
            <input
              className="infer-native-file"
              type="file"
              accept="image/*,.npy,.bin,.txt,.csv"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void onUploadInput(file);
                event.currentTarget.value = "";
              }}
            />
            <div className="infer-upload-action">选择并上传测试文件</div>
            <strong>{selectedInputPath ? `已上传：${compactPath(selectedInputPath, 48)}` : "尚未上传测试图片"}</strong>
            {selectedInputPath ? <em>文件已保存到 Linux 虚拟机，可用于 benchmark / package / board-sync / remote-infer。</em> : null}
          </label>
        </div>
      </div>

      <div className="infer-command-strip">
        <button disabled={disabledFor("check")} onClick={() => void onRunAction("check")}>Check</button>
        <button disabled={disabledFor("quantize")} onClick={() => void onRunAction("quantize")}>Quantize</button>
        <button disabled={disabledFor("benchmark")} onClick={() => void onRunAction("benchmark")} title={!hasInput ? "请先上传测试图片" : undefined}>Benchmark</button>
        <button disabled={disabledFor("package")} onClick={() => void onRunAction("package")} title={!hasInput ? "请先上传测试图片" : undefined}>Package</button>
        <button disabled={disabledFor("board-sync")} onClick={() => void onRunAction("board-sync")} title={!hasInput ? "请先上传测试图片并执行 Package" : undefined}>Board Sync</button>
        <button disabled={disabledFor("board-run")} onClick={() => void onRunAction("board-run")} title={!hasInput ? "请先上传测试图片并执行 Package" : undefined}>Remote Infer</button>
        <button disabled={disabledFor("board-deploy")} onClick={() => void onRunAction("board-deploy")}>One-click Deploy</button>
        <button disabled={running} onClick={() => void onRunAction("matrix")}>Matrix</button>
        <button disabled={running} onClick={() => void onRunAction("report")}>Report</button>
        <button disabled={running} onClick={() => void onRunAction("pdf")}>PDF</button>
      </div>

      <div className="infer-result-layout">
        <div className="infer-image-card">
          <div className="infer-card-head">
            <span>Input</span>
            <strong>{title}</strong>
          </div>

          {inputImage ? (
            <img src={fileUrl(inputImage, cacheKey)} alt="Input image" />
          ) : (
            <div className="infer-empty-visual">请先上传测试图片</div>
          )}
        </div>

        <div className="infer-image-card">
          <div className="infer-card-head">
            <span>{isDetection ? "YOLO output" : "Classification output"}</span>
            <strong>{outputNeedsRefresh ? "waiting package" : result?.status || "not run"}</strong>
          </div>

          {outputNeedsRefresh ? (
            <div className="infer-empty-visual">
              已上传新的测试图片，请重新执行 Package，然后执行 Board Sync / Remote Infer，完成后这里会显示本次图片的推理结果。
            </div>
          ) : isDetection && resultImage ? (
            <img src={fileUrl(resultImage, cacheKey)} alt="Detection result" />
          ) : prediction ? (
            <div className="infer-prediction-card">
              <span>Top-1 prediction</span>
              <strong>{prediction.label_zh || prediction.label_en || prediction.class_id || "—"}</strong>
              <em>{prediction.label_en ? `English: ${prediction.label_en}` : ""}</em>
              <div className="infer-prediction-meta">
                <div><span>Class ID</span><b>{prediction.class_id ?? "—"}</b></div>
                <div><span>Confidence</span><b>{percent(prediction.confidence)}</b></div>
                <div><span>Latency</span><b>{ms(result?.latency_ms)}</b></div>
                <div><span>Device</span><b>{result?.device || "OrangePi AIPro"}</b></div>
              </div>
            </div>
          ) : (
            <div className="infer-empty-visual">暂无板端推理结果，请先执行 Remote Infer</div>
          )}
        </div>
      </div>

      {!outputNeedsRefresh && prediction?.top5?.length ? (
        <div className="infer-table-card">
          <div className="infer-card-head"><span>Classification</span><strong>Top-5</strong></div>
          <div className="infer-top5-grid">
            {prediction.top5.slice(0, 5).map((item, index) => (
              <div key={index}>
                <span>#{index + 1}</span>
                <strong>{top5Label(item)}</strong>
                <small>{top5SubLabel(item)}</small>
                <em>{percent(item.prob as number | string | undefined)}</em>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {!outputNeedsRefresh && isDetection ? (
        <div className="infer-table-card">
          <div className="infer-card-head"><span>Detection</span><strong>{result?.detection_count ?? detections.length} objects</strong></div>
          <div className="infer-detection-table">
            <div className="infer-detection-row infer-detection-head">
              <span>Class</span><span>中文</span><span>Confidence</span><span>Box</span>
            </div>
            {detections.map((item, index) => (
              <div key={index} className="infer-detection-row">
                <span>{item.label_en || item.class_id || "—"}</span>
                <span>{item.label_zh || "—"}</span>
                <span>{percent(item.confidence)}</span>
                <code>{bboxText(item)}</code>
              </div>
            ))}
            {!detections.length ? <div className="infer-no-detection">No detections.</div> : null}
          </div>
        </div>
      ) : null}

      <div className="infer-footer-actions">
        <button onClick={onOpenRuntime}>Open Runtime Logs</button>
        <button onClick={onOpenReports}>Open Reports</button>
      </div>
    </section>
  );
}
