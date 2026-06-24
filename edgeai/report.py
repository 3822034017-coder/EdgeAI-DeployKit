"""Current-model report generation for EdgeAI DeployKit.

Key behavior:
  - `edgeai report --model <name>` uses only outputs/packages/<name>.
  - The input image in the report is copied from the current package's source_image.png,
    so it matches the image used by the latest package/remote inference.
  - matrix.json is used only as optional performance/status metadata and never causes
    unrelated models to appear in a single-model report.
"""

from __future__ import annotations

import hashlib
import html as html_module
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from .label_utils import imagenet_label, load_imagenet_labels
except Exception:  # pragma: no cover
    imagenet_label = None  # type: ignore[assignment]
    load_imagenet_labels = None  # type: ignore[assignment]

PROJECT_ROOT = Path.cwd()
REPORT_DIR = Path("reports")
REPORT_MD = REPORT_DIR / "edgeai_report.md"
REPORT_HTML = REPORT_DIR / "edgeai_report.html"
REPORT_PDF = REPORT_DIR / "edgeai_report.pdf"
MATRIX_FILE = Path("outputs/model_matrix/matrix.json")
PACKAGE_ROOT = Path("outputs/packages")

CN_LABELS = {
    "tabby": "虎斑猫",
    "tiger cat": "虎斑猫",
    "Persian cat": "波斯猫",
    "Siamese cat": "暹罗猫",
    "Egyptian cat": "埃及猫",
    "paper towel": "纸巾",
    "tub": "浴缸",
    "car": "汽车",
    "person": "人",
    "bus": "公交车",
    "truck": "卡车",
    "bicycle": "自行车",
    "motorcycle": "摩托车",
    "dog": "狗",
    "cat": "猫",
}


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {} if default is None else default


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  -> {path}")


def _load_matrix() -> list[dict[str, Any]]:
    data = _read_json(MATRIX_FILE, [])
    return data if isinstance(data, list) else []


def load_matrix() -> list[dict[str, Any]]:
    return _load_matrix()


def _safe_model_name(value: str | None) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip().replace("\\", "/").rstrip("/")
    if not text:
        return None
    # Model path such as models/zoo/mnist/model.onnx -> mnist
    p = Path(text)
    if p.name.lower() == "model.onnx" and p.parent.name:
        return p.parent.name
    if text.endswith(".onnx"):
        return p.stem
    if "/" in text:
        return p.name
    return text


def _latest_package_name() -> str:
    packages = [p for p in PACKAGE_ROOT.iterdir() if p.is_dir()] if PACKAGE_ROOT.exists() else []
    scored = []
    for p in packages:
        candidates = [p / "board_result.json", p / "model.json", p / "source_image.png", p]
        mtimes = [c.stat().st_mtime for c in candidates if c.exists()]
        if mtimes:
            scored.append((max(mtimes), p.name))
    if scored:
        return sorted(scored, reverse=True)[0][1]
    matrix = _load_matrix()
    if matrix:
        return str(matrix[-1].get("model") or matrix[-1].get("model_name") or "model")
    return "model"


def _package_dir(model: str | None) -> Path:
    name = _safe_model_name(model) or _latest_package_name()
    direct = PACKAGE_ROOT / name
    if direct.exists():
        return direct
    # fallback: match by matrix package_dir
    for row in _load_matrix():
        if str(row.get("model") or "") == name:
            pkg = Path(str(row.get("package_dir") or ""))
            if pkg.exists():
                return pkg
    return direct


def _matching_matrix_row(model_name: str, pkg_dir: Path) -> dict[str, Any]:
    pkg_norm = str(pkg_dir).replace("\\", "/")
    for row in _load_matrix():
        row_model = str(row.get("model") or row.get("model_name") or "")
        row_pkg = str(row.get("package_dir") or "").replace("\\", "/")
        if row_model == model_name or row_pkg.endswith(pkg_norm) or row_pkg.endswith("/" + model_name):
            return row
    return {}


def _model_type(model_name: str, model_json: dict[str, Any], board_result: dict[str, Any], row: dict[str, Any]) -> str:
    contract = model_json.get("deployment_contract") if isinstance(model_json.get("deployment_contract"), dict) else {}
    value = (
        contract.get("model_type")
        or model_json.get("model_type")
        or board_result.get("model_type")
        or row.get("model_type")
        or model_name
    )
    text = str(value or model_name).lower()
    if "yolo" in text or "yolo" in model_name.lower():
        return "yolov5n"
    if "mobilenet" in text or "mobilenet" in model_name.lower():
        return "mobilenetv2"
    if "resnet" in text or "resnet" in model_name.lower():
        return "resnet18"
    if "mnist" in text or "mnist" in model_name.lower():
        return "mnist"
    return str(value or model_name)


def _status_from_result(payload: dict[str, Any], success_value: str = "success") -> str:
    status = str(payload.get("status") or "").lower()
    if status in {"success", "ok", "pass", "passed"}:
        return "PASS"
    if status in {"failed", "fail", "error"}:
        return "FAIL"
    return "—"


def _num(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _fmt_ms(value: Any) -> str:
    v = _num(value)
    return "—" if v is None else f"{v:.3f} ms"


def _fmt_prob(value: Any) -> str:
    v = _num(value)
    return "—" if v is None else f"{v:.4f}"


def _cn(label: Any) -> str:
    if not label:
        return "—"
    return CN_LABELS.get(str(label), "—")


def _classification_label(index: Any, existing: Any, model_type: str) -> str:
    if existing:
        return str(existing)
    if model_type in {"mobilenetv2", "resnet18"} and imagenet_label is not None:
        try:
            label = imagenet_label(index)
            if label:
                return str(label)
        except Exception:
            return "—"
    return "—"


def _sha_file(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()[:12]
    except Exception:
        return str(int(path.stat().st_mtime)) if path.exists() else "missing"


def _copy_asset(src: Path | str | None, assets_dir: Path, prefix: str) -> Optional[str]:
    if not src:
        return None
    path = Path(str(src)).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve()
    if not path.exists() or not path.is_file():
        return None
    assets_dir.mkdir(parents=True, exist_ok=True)
    safe_prefix = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in prefix)
    dst = assets_dir / f"{safe_prefix}_{_sha_file(path)}{path.suffix.lower() or '.png'}"
    shutil.copy2(path, dst)
    return f"assets/{dst.name}"


def _input_source_path(pkg_dir: Path, model_json: dict[str, Any], row: dict[str, Any]) -> tuple[Optional[Path], str]:
    src_img = pkg_dir / "source_image.png"
    if src_img.exists():
        source_info = model_json.get("input_source") if isinstance(model_json.get("input_source"), dict) else {}
        original = source_info.get("source") or row.get("input_file") or str(src_img)
        return src_img, str(original)
    source_info = model_json.get("input_source") if isinstance(model_json.get("input_source"), dict) else {}
    candidate = source_info.get("source") or row.get("input_file")
    if candidate:
        return Path(str(candidate)), str(candidate)
    return None, "—"


def _annotated_image_path(pkg_dir: Path, board_result: dict[str, Any], row: dict[str, Any]) -> Optional[Path]:
    candidates = [
        board_result.get("annotated_image"),
        row.get("annotated_image"),
        pkg_dir / "yolo_result.jpg",
        pkg_dir / "yolo_result.png",
    ]
    for item in candidates:
        if not item:
            continue
        p = item if isinstance(item, Path) else Path(str(item))
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if p.exists():
            return p
    return None


def _current_model_payload(model: str | None) -> dict[str, Any]:
    pkg = _package_dir(model)
    model_name = pkg.name if pkg.name else (_safe_model_name(model) or _latest_package_name())
    model_json = _read_json(pkg / "model.json", {})
    board_result = _read_json(pkg / "board_result.json", {})
    board_run_result = _read_json(pkg / "board_run_result.json", {})
    convert_result = _read_json(pkg / "convert_result.json", {})
    row = _matching_matrix_row(model_name, pkg)
    mtype = _model_type(model_name, model_json, board_result, row)
    input_img, original_input = _input_source_path(pkg, model_json, row)
    annotated = _annotated_image_path(pkg, board_result, row)
    return {
        "model_name": model_name,
        "model_type": mtype,
        "package_dir": pkg,
        "model_json": model_json,
        "board_result": board_result,
        "board_run_result": board_run_result,
        "convert_result": convert_result,
        "matrix_row": row,
        "input_image": input_img,
        "original_input": original_input,
        "annotated_image": annotated,
    }


def _metric(payload: dict[str, Any], *keys: str) -> Any:
    for source_name in ("board_result", "matrix_row", "model_json"):
        source = payload.get(source_name) or {}
        if not isinstance(source, dict):
            continue
        for key in keys:
            if source.get(key) is not None:
                return source.get(key)
    return None


def generate_matrix_markdown(model: Optional[str] = None) -> Path:
    payload = _current_model_payload(model)
    model_name = payload["model_name"]
    model_type = payload["model_type"]
    pkg_dir: Path = payload["package_dir"]
    model_json = payload["model_json"]
    board_result = payload["board_result"]
    board_run_result = payload["board_run_result"]
    convert_result = payload["convert_result"]
    row = payload["matrix_row"]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    assets_dir = REPORT_DIR / "assets"
    # Clear report assets so stale images are not reused by Markdown/PDF.
    if assets_dir.exists():
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    input_rel = _copy_asset(payload.get("input_image"), assets_dir, f"{model_name}_input")
    ann_rel = _copy_asset(payload.get("annotated_image"), assets_dir, f"{model_name}_result")

    board_lat = board_result.get("latency_ms") or row.get("board_latency_ms")
    pc_avg = row.get("avg_latency_ms")
    pc_p95 = row.get("p95_ms")
    input_shape = (
        board_result.get("input_shape")
        or (model_json.get("deployment_contract") or {}).get("input_shape")
        or row.get("input_shape")
        or "—"
    )
    input_name = board_result.get("input_name") or (model_json.get("deployment_contract") or {}).get("input_name") or row.get("input_name") or "—"

    om_status = _status_from_result(convert_result)
    if om_status == "—" and (pkg_dir / "model.om").exists():
        om_status = "PASS"
    board_status = _status_from_result(board_result) if board_result else _status_from_result(board_run_result)
    if board_status == "—" and board_run_result:
        board_status = _status_from_result(board_run_result)

    lines: list[str] = []
    lines += [
        "# EdgeAI Current Model Report",
        "",
        f"> Generated: {now}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"本报告只包含当前选择模型 **{model_name}**，数据来源为 `{pkg_dir}` 下的最新 `model.json`、`board_result.json`、`source_image.png` 和相关运行产物。",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Current Model | `{model_name}` |",
        f"| Model Type | `{model_type}` |",
        f"| Package | `{pkg_dir}` |",
        f"| Input Name | `{input_name}` |",
        f"| Input Shape | `{input_shape}` |",
        f"| OM Convert | {om_status} |",
        f"| Board Run | {board_status} |",
        f"| Board Latency | {_fmt_ms(board_lat)} |",
        "",
        "---",
        "",
        "## Test Environment & Method",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Host Project | EdgeAI DeployKit |",
        "| Target Board | Orange Pi AIPro |",
        "| Runtime | airloader / QEMU fallback |",
        f"| Report Source | `{pkg_dir}` |",
        "| Output Artifacts | `reports/edgeai_report.md`, `reports/edgeai_report.html`, `reports/edgeai_report.pdf` |",
        "",
        "## Deployment Matrix",
        "",
        "| Model | Type | PC Benchmark | OM Convert | Board Run | PC Avg(ms) | Board Avg(ms) | P95(ms) |",
        "|---|---|---|---|---|---:|---:|---:|",
        f"| {model_name} | {model_type} | {row.get('benchmark', '—')} | {om_status} | {board_status} | {_num(pc_avg, 0) or '—'} | {_num(board_lat, 0) or '—'} | {_num(pc_p95, 0) or '—'} |",
        "",
        "---",
        "",
        "## Model Details",
        "",
        f"### {model_name} ({model_type})",
        "",
        "#### Deployment Readiness",
        "",
        "| Stage | Status |",
        "|---|---|",
        f"| ONNX Check | {row.get('onnx_check', 'NOT RUN')} |",
        f"| PC Benchmark | {row.get('benchmark', '—')} |",
        f"| OM Convert | {om_status} |",
        f"| Board Run | {board_status} |",
        "",
        "#### Performance",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Avg Latency (PC) | {_fmt_ms(pc_avg)} |",
        f"| P50 Latency (PC) | {_fmt_ms(row.get('p50_ms'))} |",
        f"| P95 Latency (PC) | {_fmt_ms(pc_p95)} |",
        f"| Min Latency (PC) | {_fmt_ms(row.get('min_ms'))} |",
        f"| Max Latency (PC) | {_fmt_ms(row.get('max_ms'))} |",
        f"| Board Latency | {_fmt_ms(board_lat)} |",
        "",
        "#### Input",
        "",
        f"Test image: `{payload.get('original_input') or '—'}`",
        "",
    ]

    if input_rel:
        lines += [f"![Input]({input_rel})", ""]
    else:
        lines += ["_No source image found in current package._", ""]

    # Result section
    lines += ["#### Result", ""]
    detections = board_result.get("detections") if isinstance(board_result.get("detections"), list) else []
    det_count = board_result.get("detection_count")
    if det_count is None and detections:
        det_count = len(detections)

    if det_count is not None and int(det_count or 0) >= 0 and ("yolo" in model_type.lower() or detections):
        lines += [f"Detected objects: **{int(det_count or 0)}**", ""]
        lines += ["| # | Class ID | Label | 中文标签 | Confidence |", "|---:|---:|---|---|---:|"]
        for i, det in enumerate(detections[:20], 1):
            label = det.get("label") or det.get("class_name") or "—"
            cls_id = det.get("class_id", "—")
            conf = det.get("confidence", det.get("score"))
            lines.append(f"| {i} | {cls_id} | {label} | {_cn(label)} | {_fmt_prob(conf)} |")
        lines.append("")
        if ann_rel:
            lines += ["Annotated result:", "", f"![Detections]({ann_rel})", ""]
    else:
        top1 = board_result.get("top1", board_result.get("predict", row.get("top1", row.get("predict"))))
        top1_label = _classification_label(top1, board_result.get("top1_label") or board_result.get("predict_label") or row.get("top1_label") or row.get("predict_label"), model_type)
        lines += [f"Prediction: **{top1 if top1 is not None else '—'} / {top1_label} / {_cn(top1_label)}**", ""]
        top5 = board_result.get("top5") or row.get("top5") or []
        if isinstance(top5, list) and top5:
            lines += ["| Rank | Class ID | English Label | 中文标签 | Probability |", "|---:|---:|---|---|---:|"]
            for rank, item in enumerate(top5[:5], 1):
                idx = item.get("index", item.get("class_id", "—")) if isinstance(item, dict) else "—"
                label = _classification_label(idx, item.get("label") if isinstance(item, dict) else None, model_type)
                prob = item.get("prob", item.get("probability")) if isinstance(item, dict) else None
                lines.append(f"| {rank} | {idx} | {label} | {_cn(label)} | {_fmt_prob(prob)} |")
            lines.append("")

    lines += [
        "#### Board Results",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Status | {board_result.get('status') or board_run_result.get('status') or '—'} |",
        f"| Runtime | {board_result.get('runtime', '—')} |",
        f"| Board Latency | {_fmt_ms(board_lat)} |",
    ]
    if board_result.get("top1") is not None:
        label = _classification_label(board_result.get("top1"), board_result.get("top1_label") or board_result.get("predict_label"), model_type)
        lines.append(f"| Top-1 | {board_result.get('top1')} / {label} / {_cn(label)} |")
    if det_count is not None and ("yolo" in model_type.lower() or detections):
        lines.append(f"| Detections | {int(det_count or 0)} |")
    lines += [
        "",
        "#### Artifact Trace",
        "",
        "| Artifact | Path |",
        "|---|---|",
        f"| Package | `{pkg_dir}` |",
        f"| Model JSON | `{pkg_dir / 'model.json'}` |",
        f"| Source Image | `{pkg_dir / 'source_image.png'}` |",
        f"| Board Result | `{pkg_dir / 'board_result.json'}` |",
        f"| OM Convert Result | `{pkg_dir / 'convert_result.json'}` |",
        f"| Annotated Result | `{payload.get('annotated_image') or '—'}` |",
        "",
        "---",
        "",
        "## Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
        "| Markdown Report | `reports/edgeai_report.md` |",
        "| HTML Report | `reports/edgeai_report.html` |",
        "| PDF Report | `reports/edgeai_report.pdf` |",
        f"| Current Package | `{pkg_dir}` |",
        "",
        "## Conclusion",
        "",
        f"当前报告只针对 **{model_name}**。若输入图片已更换，请先完成 Package / Board Sync / Remote Infer，再重新生成本报告。",
        "",
    ]

    _write(REPORT_MD, "\n".join(lines))
    return REPORT_MD


def _markdown_to_html_text(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    out: list[str] = []
    in_table = False

    def close_table():
        nonlocal in_table
        if in_table:
            out.append("</table>")
            in_table = False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            close_table()
            continue
        if stripped == "---":
            close_table(); out.append("<hr>"); continue
        if stripped.startswith("# "):
            close_table(); out.append(f"<h1>{html_module.escape(stripped[2:])}</h1>"); continue
        if stripped.startswith("## "):
            close_table(); out.append(f"<h2>{html_module.escape(stripped[3:])}</h2>"); continue
        if stripped.startswith("### "):
            close_table(); out.append(f"<h3>{html_module.escape(stripped[4:])}</h3>"); continue
        if stripped.startswith("#### "):
            close_table(); out.append(f"<h4>{html_module.escape(stripped[5:])}</h4>"); continue
        if stripped.startswith("![") and "](" in stripped and stripped.endswith(")"):
            close_table()
            alt = stripped[2:stripped.index("](")]
            src = stripped[stripped.index("](") + 2:-1]
            out.append(f'<figure><img src="{html_module.escape(src)}" alt="{html_module.escape(alt)}"><figcaption>{html_module.escape(alt)}</figcaption></figure>')
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
            tag = "th" if not out[-1].startswith("<tr>") and len(out) and out[-1] == "<table>" else "td"
            out.append("<tr>" + "".join(f"<{tag}>{html_module.escape(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        close_table()
        safe = html_module.escape(stripped)
        safe = safe.replace("**", "")
        out.append(f"<p>{safe}</p>")
    close_table()
    return "\n".join(out)


def generate_matrix_html(model: Optional[str] = None) -> Path:
    md = REPORT_MD if REPORT_MD.exists() else generate_matrix_markdown(model=model)
    body = _markdown_to_html_text(md)
    html_text = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\">
<title>EdgeAI Current Model Report</title>
<style>
body {{ font-family: 'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif; margin: 36px auto; max-width: 1080px; color:#111827; line-height:1.75; }}
h1 {{ font-size: 30px; }} h2 {{ margin-top: 30px; border-top: 2px solid #111827; padding-top: 20px; }} h3 {{ font-size: 22px; }} h4 {{ font-size: 18px; margin-top: 24px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0 22px; }}
th, td {{ border: 1px solid #d7dce3; padding: 9px 12px; text-align: left; vertical-align: top; }}
th {{ background: #f3f5f8; font-weight: 700; }}
img {{ max-width: 100%; border-radius: 6px; }}
figure {{ margin: 12px 0 24px; }} figcaption {{ color: #64748b; font-size: 13px; }}
code {{ background:#f3f4f6; padding:2px 5px; border-radius:4px; }}
</style>
</head><body>{body}</body></html>"""
    _write(REPORT_HTML, html_text)
    return REPORT_HTML


def markdown_to_pdf(md_path: Optional[Path] = None, pdf_path: Optional[Path] = None) -> Path:
    md = Path(md_path or REPORT_MD).resolve()
    pdf = Path(pdf_path or REPORT_PDF).resolve()
    if not md.exists():
        raise FileNotFoundError(f"Markdown not found: {md}. Run 'edgeai report --model <name>' first.")
    pdf.parent.mkdir(parents=True, exist_ok=True)

    try:
        from weasyprint import HTML as WHTML
        html_file = generate_matrix_html(None).resolve()
        WHTML(filename=str(html_file)).write_pdf(str(pdf))
        print(f"  -> {pdf}")
        return pdf
    except Exception as exc:
        print(f"[weasyprint] fallback/failed: {exc}")

    if shutil.which("pandoc"):
        cmd = [
            "pandoc", str(md), "-o", str(pdf),
            "--pdf-engine=xelatex",
            "-V", "mainfont=Noto Sans CJK SC",
            "-V", "geometry:margin=2.2cm",
            "--resource-path", str(md.parent),
        ]
        subprocess.run(cmd, check=True)
        print(f"  -> {pdf}")
        return pdf

    raise RuntimeError("Cannot generate PDF: install weasyprint or pandoc/xelatex.")


# Backward-compatible helpers imported by cli.py

def generate_markdown_report(input_path: Path, output_path: Path) -> None:
    data = _read_json(Path(input_path), {})
    content = "# EdgeAI Benchmark Report\n\n```json\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```\n"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(content, encoding="utf-8")
    print(f"Markdown report saved to: {output_path}")


def generate_html_report(input_path: Path, output_path: Path) -> None:
    src = Path(input_path)
    text = src.read_text(encoding="utf-8", errors="ignore") if src.exists() else ""
    html_text = "<pre>" + html_module.escape(text) + "</pre>"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html_text, encoding="utf-8")
    print(f"HTML report saved to: {output_path}")


def compare_reports(fp32: Optional[Path] = None, int8: Optional[Path] = None, output: Optional[Path] = None) -> None:
    matrix = _load_matrix()
    print(json.dumps(matrix, indent=2, ensure_ascii=False))


# ==== EdgeAI global edgeai_report PDF disabled v3 ====
# Package-local report generation must not call reports/edgeai_report.* because it
# can leak stale YOLO/board reports into unrelated model packages.

def markdown_to_pdf(md_path=None, pdf_path=None):  # type: ignore[override]
    from pathlib import Path as _Path
    import os as _os
    if md_path is None or pdf_path is None:
        raise RuntimeError(
            "Global PDF defaults are disabled. Pass explicit package-local paths: "
            "outputs/packages/<package>/report.md -> report.pdf."
        )
    md = _Path(md_path).expanduser().resolve()
    pdf = _Path(pdf_path).expanduser().resolve()
    joined = f"{md}\n{pdf}"
    if "reports/edgeai_report" in joined and _os.environ.get("EDGEAI_ALLOW_LEGACY_GLOBAL_REPORT") != "1":
        raise RuntimeError(
            "Legacy global PDF reports/edgeai_report.* is disabled. "
            "Use package-local reports under outputs/packages/<package>/ instead."
        )
    from .package_pdf import markdown_to_pdf_strict as _strict
    return _strict(md_path=md, pdf_path=pdf, html_path=pdf.with_suffix(".html"))
