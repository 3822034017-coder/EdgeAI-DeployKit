from __future__ import annotations

import json
import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fmt_shape(shape: Any) -> str:
    if isinstance(shape, list):
        return "[" + ", ".join(str(x) for x in shape) + "]"
    return str(shape)


def _fmt_bool(v: Any) -> str:
    return "是" if bool(v) else "否"


def _short(v: Any, max_len: int = 160) -> str:
    s = str(v)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


def _load_label_map(package_dir: Path, extra_candidates: Optional[Iterable[Path]] = None) -> Tuple[Optional[Any], Optional[Path]]:
    """Load optional labels.

    Supported formats:
    - label_map.json as list: ["class0", "class1", ...]
    - label_map.json as dict: {"0": "class0", "1": "class1"}
    - imagenet_classes.txt: one label per line
    """
    candidates = list(extra_candidates or []) + [
        package_dir / "label_map.json",
        package_dir / "labels.json",
        package_dir / "imagenet_classes.txt",
        package_dir.parent.parent.parent / "imagenet_classes.txt",
        Path("imagenet_classes.txt"),
        Path("models/labels/imagenet_classes.txt"),
        Path("labels/imagenet_classes.txt"),
    ]
    for path in candidates:
        try:
            if not path.exists():
                continue
            if path.suffix.lower() == ".json":
                return json.loads(path.read_text(encoding="utf-8")), path
            if path.suffix.lower() == ".txt":
                labels = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
                return labels, path
        except Exception:
            continue
    return None, None


def _load_zh_overrides() -> Dict[str, str]:
    candidates = [
        Path("models/labels/imagenet_zh_overrides.json"),
        Path(__file__).resolve().parents[1] / "models" / "labels" / "imagenet_zh_overrides.json",
    ]
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items() if str(k).strip() and str(v).strip()}
        except Exception:
            continue
    return {}


def _localize_label(label: Any, label_language: str, overrides: Dict[str, str]) -> Tuple[Any, Optional[str]]:
    if not label or not str(label_language).lower().startswith("zh"):
        return label, None
    text = str(label)
    localized = overrides.get(text)
    if not localized:
        return label, None
    return localized, text


def _label_for(label_map: Any, index: Any) -> Optional[str]:
    if label_map is None:
        return None
    try:
        i = int(index)
    except Exception:
        return None
    if isinstance(label_map, list):
        if 0 <= i < len(label_map):
            return str(label_map[i])
        return None
    if isinstance(label_map, dict):
        for key in (str(i), i):
            if key in label_map:
                return str(label_map[key])
    return None


def _top_ops(operator_count: Dict[str, Any], limit: int = 20) -> List[Tuple[str, int]]:
    items: List[Tuple[str, int]] = []
    for k, v in (operator_count or {}).items():
        try:
            items.append((str(k), int(v)))
        except Exception:
            pass
    return sorted(items, key=lambda x: (-x[1], x[0]))[:limit]


def _table(headers: List[str], rows: Iterable[Iterable[Any]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(_short(x) for x in row) + " |")
    return "\n".join(out)


def _relative_image_ref(md_path: Path, image_path: Path) -> str:
    try:
        return image_path.resolve().relative_to(md_path.parent.resolve()).as_posix()
    except Exception:
        try:
            return image_path.relative_to(md_path.parent).as_posix()
        except Exception:
            return str(image_path)


def _find_existing(package_dir: Path, names: Iterable[str]) -> Optional[Path]:
    for name in names:
        path = package_dir / name
        if path.exists() and path.is_file():
            return path
    return None


def _find_source_input(package_dir: Path) -> Optional[Path]:
    exact = _find_existing(package_dir, [
        "source_input.png", "source_input.jpg", "source_input.jpeg", "source_input.bmp", "source_input.webp",
    ])
    if exact:
        return exact
    for pattern in ("source_input.*", "input_image.*", "input.*"):
        for p in sorted(package_dir.glob(pattern)):
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"} and p.is_file():
                return p
    return None


def _find_output_visual(package_dir: Path) -> Optional[Path]:
    exact = _find_existing(package_dir, [
        "local_visualization.png", "local_visualization.jpg", "local_yolo_result.jpg", "local_result.jpg",
        "result.jpg", "result.png", "output.jpg", "output.png", "yolo_result.jpg", "prediction.jpg",
    ])
    if exact:
        return exact
    for pattern in ("*result*.jpg", "*result*.png", "*visual*.jpg", "*visual*.png", "*output*.jpg", "*output*.png"):
        for p in sorted(package_dir.glob(pattern)):
            if p.name == "source_input.png":
                continue
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"} and p.is_file():
                return p
    return None


def _contains_cjk(value: Any) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(value or ""))


def _pil_font_candidates(prefer_cjk: bool) -> List[str]:
    cjk_candidates = [
        # openEuler / common Linux packages
        "/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Medium.otf",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Medium.ttc",
        "/usr/share/fonts/google-droid-fonts/DroidSansFallback.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    latin_candidates = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "Arial.ttf",
    ]
    return (cjk_candidates + latin_candidates) if prefer_cjk else latin_candidates


def _load_pil_font(ImageFont: Any, size: int, prefer_cjk: bool = False) -> Tuple[Any, Optional[str]]:
    for candidate in _pil_font_candidates(prefer_cjk):
        try:
            if ("/" in candidate or ":" in candidate) and not Path(candidate).exists():
                continue
            return ImageFont.truetype(candidate, size), candidate
        except Exception:
            continue
    return ImageFont.load_default(), None


def _is_cjk_font(font_path: Optional[str]) -> bool:
    if not font_path:
        return False
    name = font_path.lower()
    return any(token in name for token in ("noto", "cjk", "droid", "pingfang", "heiti", "msyh", "simhei", "simsun", "uming"))


def _generate_topk_image(package_dir: Path, topk: List[Dict[str, Any]]) -> Optional[Path]:
    """Generate a small result image for classification-like TopK output.

    This makes PDF review possible even when the model output is not a detection image.
    It is intentionally optional: if Pillow is missing or drawing fails, the report still
    contains the TopK table.
    """
    if not topk:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    try:
        rows = topk[:5]
        width = 1100
        row_h = 70
        height = 120 + row_h * len(rows)
        img = Image.new("RGB", (width, height), "#0f172a")
        draw = ImageDraw.Draw(img)
        prefer_cjk = any(_contains_cjk(item.get("label")) for item in rows)
        font_title, _ = _load_pil_font(ImageFont, 34, prefer_cjk=prefer_cjk)
        font, _ = _load_pil_font(ImageFont, 24, prefer_cjk=prefer_cjk)
        font_small, font_small_path = _load_pil_font(ImageFont, 20, prefer_cjk=prefer_cjk)
        cjk_font_ready = _is_cjk_font(font_small_path)

        draw.text((40, 28), "Local Inference TopK Result", fill="#e5eefc", font=font_title)
        scores = []
        for item in rows:
            try:
                scores.append(float(item.get("score", 0)))
            except Exception:
                scores.append(0.0)
        min_s, max_s = min(scores), max(scores)
        span = max(max_s - min_s, 1e-9)

        for i, item in enumerate(rows):
            y = 100 + i * row_h
            idx = item.get("index")
            label = item.get("label") or "未提供 label_map"
            if _contains_cjk(label) and not cjk_font_ready:
                label = item.get("label_en") or label
            try:
                score = float(item.get("score", 0))
            except Exception:
                score = 0.0
            frac = (score - min_s) / span if span else 1.0
            # Keep the score readable inside the bar and leave a stable label column.
            bar_w = int(320 + frac * 460)
            draw.rounded_rectangle((40, y + 14, 40 + bar_w, y + 52), radius=12, fill="#38bdf8")
            draw.text((56, y + 18), f"#{i+1}  index={idx}  score={score:.4f}", fill="#020617", font=font_small)
            draw.text((850, y + 18), str(label)[:26], fill="#e5eefc", font=font_small)

        out = package_dir / "local_topk_result.png"
        img.save(out)
        return out
    except Exception:
        return None


def _try_generate_pdf(md_path: Path, pdf_path: Path) -> Optional[Path]:
    """Use the existing project Markdown→PDF converter when available.

    The existing converter supports weasyprint and pandoc. If neither exists, it may
    return a path without creating the file; in that case we report no PDF.
    """
    try:
        from .report import markdown_to_pdf
        candidate = markdown_to_pdf(md_path=md_path, pdf_path=pdf_path)
        candidate = Path(candidate)
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    except Exception:
        return None
    return None


def generate_local_package_report(
    package_dir: Path,
    output: Optional[Path] = None,
    mirror_to_reports: bool = True,
    title: Optional[str] = None,
    generate_pdf: bool = True,
) -> Dict[str, Any]:
    """Generate Markdown + optional PDF report for the new local-run package flow."""
    package_dir = Path(package_dir)
    if not package_dir.exists():
        raise FileNotFoundError(f"Package directory not found: {package_dir}")

    model_json = _read_json(package_dir / "model.json", {}) or {}
    signature = _read_json(package_dir / "model_signature.json", {}) or {}
    preprocess = _read_json(package_dir / "preprocess.json", {}) or {}
    local_result = _read_json(package_dir / "local_result.json", {}) or {}
    operator_report = _read_json(package_dir / "operator_report.json", {}) or {}
    convert_result = _read_json(package_dir / "convert_result.json", {}) or {}
    task = _read_json(package_dir / "model_task.json", {}) or {}
    output_cfg = task.get("output") if isinstance(task.get("output"), dict) else {}
    label_language = str(output_cfg.get("label_language") or "en")
    zh_overrides = _load_zh_overrides()

    model_name = str(model_json.get("model_name") or package_dir.name)
    title = title or f"EdgeAI-DeployKit 本地推理报告：{model_name}"

    label_candidates: List[Path] = []
    configured_label_map = output_cfg.get("label_map")
    if configured_label_map:
        configured = Path(str(configured_label_map))
        label_candidates.extend([
            package_dir / configured,
            Path(str(configured_label_map)),
            Path(__file__).resolve().parents[1] / configured,
        ])
    label_map, label_map_path = _load_label_map(package_dir, label_candidates)
    topk = list(local_result.get("topk") or [])
    enriched_topk: List[Dict[str, Any]] = []
    for item in topk:
        if not isinstance(item, dict):
            continue
        item = dict(item)
        if item.get("label") in (None, ""):
            item["label"] = _label_for(label_map, item.get("index"))
        item["label"], label_en = _localize_label(item.get("label"), label_language, zh_overrides)
        if label_en:
            item["label_en"] = label_en
        enriched_topk.append(item)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system = platform.system()
    machine = platform.machine()

    output = Path(output) if output else package_dir / "report.md"

    source_input_img = _find_source_input(package_dir)
    output_visual_img = _find_output_visual(package_dir)
    topk_img = _generate_topk_image(package_dir, enriched_topk) if enriched_topk else None

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> 生成时间：{generated_at}")
    lines.append(f"> Package：`{package_dir}`")
    lines.append("")

    # Summary
    success = bool(local_result.get("success")) if local_result else False
    latency = local_result.get("latency_ms") if local_result else None
    backend = local_result.get("backend") or "onnxruntime"
    provider = local_result.get("provider") or "CPUExecutionProvider"
    lines.append("## 1. 结论")
    lines.append("")
    if local_result:
        lines.append(_table(
            ["项目", "结果"],
            [
                ["本地推理是否成功", "成功" if success else "失败"],
                ["推理后端", backend],
                ["执行 Provider", provider],
                ["运行平台", f"{system} / {machine}"],
                ["单次推理耗时", f"{latency} ms" if latency is not None else "未知"],
            ],
        ))
    else:
        lines.append("未发现 `local_result.json`，请先执行：")
        lines.append("")
        lines.append("```bash")
        lines.append(f"edgeai local-run --package {package_dir}")
        lines.append("```")
    lines.append("")

    # Visual proof
    lines.append("## 2. 输入与输出预览")
    lines.append("")
    if source_input_img:
        lines.append("### 输入图片")
        lines.append("")
        lines.append(f"![输入图片]({_relative_image_ref(output, source_input_img)})")
        lines.append("")
    else:
        lines.append("- 未发现输入图片。若输入是 `.npy` 或表格数据，请查看 `input.npy` 与预处理配置。")
        lines.append("")

    if output_visual_img:
        lines.append("### 输出可视化结果")
        lines.append("")
        lines.append(f"![输出可视化结果]({_relative_image_ref(output, output_visual_img)})")
        lines.append("")
    elif topk_img:
        lines.append("### 输出结果 TopK 可视化")
        lines.append("")
        lines.append(f"![TopK 输出结果]({_relative_image_ref(output, topk_img)})")
        lines.append("")
    else:
        lines.append("- 当前模型输出为 tensor，没有生成图片类输出。请查看下方 TopK 或输出 preview。")
        lines.append("")

    # Model source
    lines.append("## 3. 模型来源")
    lines.append("")
    lines.append(_table(
        ["字段", "内容"],
        [
            ["模型名称", model_name],
            ["来源框架", model_json.get("framework") or convert_result.get("source_framework") or "unknown"],
            ["ONNX 模型", package_dir / "model.onnx"],
            ["原始模型目录", package_dir / "source_model"],
        ],
    ))
    lines.append("")

    # Signature
    lines.append("## 4. ONNX 输入输出信息")
    lines.append("")
    opset = signature.get("opset") or []
    if opset:
        opset_text = ", ".join(f"{x.get('domain', 'ai.onnx')}:{x.get('version')}" for x in opset if isinstance(x, dict))
        lines.append(f"- opset：`{opset_text}`")
    if signature.get("ir_version") is not None:
        lines.append(f"- IR version：`{signature.get('ir_version')}`")
    if signature.get("producer_name"):
        lines.append(f"- producer：`{signature.get('producer_name')} {signature.get('producer_version', '')}`")
    lines.append(f"- 是否包含动态 shape：{_fmt_bool(signature.get('has_dynamic_shape'))}")
    lines.append("")

    inputs = signature.get("inputs") or []
    if inputs:
        lines.append("### 输入")
        lines.append("")
        lines.append(_table(
            ["name", "shape", "dtype", "layout_guess", "dynamic"],
            [[x.get("name"), _fmt_shape(x.get("shape")), x.get("dtype"), x.get("layout_guess"), x.get("dynamic")] for x in inputs],
        ))
        lines.append("")

    outputs = signature.get("outputs") or []
    if outputs:
        lines.append("### 输出")
        lines.append("")
        lines.append(_table(
            ["name", "shape", "dtype", "dynamic"],
            [[x.get("name"), _fmt_shape(x.get("shape")), x.get("dtype"), x.get("dynamic")] for x in outputs],
        ))
        lines.append("")

    # Preprocess
    lines.append("## 5. 输入预处理配置")
    lines.append("")
    if preprocess:
        rows = [
            ["输入类型", preprocess.get("input_type")],
            ["输入名", preprocess.get("input_name")],
            ["layout", preprocess.get("layout")],
            ["color_format", preprocess.get("color_format")],
            ["dtype", preprocess.get("dtype")],
        ]
        resize = preprocess.get("resize") or {}
        if resize:
            rows.append(["resize", f"{resize.get('mode', 'resize')} {resize.get('width')}x{resize.get('height')}"])
        norm = preprocess.get("normalization") or {}
        if norm:
            rows.append(["normalization", f"scale={norm.get('scale')}, mean={norm.get('mean')}, std={norm.get('std')}"])
        lines.append(_table(["字段", "内容"], rows))
        note = preprocess.get("note")
        if note:
            lines.append("")
            lines.append(f"> 注意：{note}")
    else:
        lines.append("未发现 `preprocess.json`，请先执行 `edgeai prepare-input`。")
    lines.append("")

    # Result
    lines.append("## 6. 本地推理结果")
    lines.append("")
    if local_result:
        inp = local_result.get("input") or {}
        first_output = (local_result.get("outputs") or [{}])[0] if local_result.get("outputs") else {}
        lines.append(_table(
            ["字段", "内容"],
            [
                ["输入 tensor", inp.get("path")],
                ["输入 shape", _fmt_shape(inp.get("shape"))],
                ["输入 dtype", inp.get("dtype")],
                ["输出 tensor", first_output.get("path")],
                ["repeat", local_result.get("repeat")],
                ["latency_ms", local_result.get("latency_ms")],
            ],
        ))
        lines.append("")
        if enriched_topk:
            lines.append("### TopK")
            lines.append("")
            has_label_en = any(x.get("label_en") for x in enriched_topk)
            headers = ["rank", "index", "label", "score"]
            rows = [[i + 1, x.get("index"), x.get("label") or "未提供 label_map", x.get("score")] for i, x in enumerate(enriched_topk)]
            if has_label_en:
                headers = ["rank", "index", "中文标签", "英文标签", "score"]
                rows = [[i + 1, x.get("index"), x.get("label") or "未提供 label_map", x.get("label_en") or "", x.get("score")] for i, x in enumerate(enriched_topk)]
            lines.append(_table(
                headers,
                rows,
            ))
            lines.append("")
            if label_map_path:
                lines.append(f"> 已读取标签文件：`{label_map_path}`")
            else:
                lines.append("> 当前未发现 `label_map.json` 或 `imagenet_classes.txt`，因此 TopK 只能显示类别 index。")
            lines.append("")
        elif first_output.get("preview"):
            lines.append("### 输出 preview")
            lines.append("")
            lines.append("```text")
            lines.append(str(first_output.get("preview")))
            lines.append("```")
            lines.append("")
    else:
        lines.append("暂无本地推理结果。")
        lines.append("")

    # Operators
    lines.append("## 7. 算子统计")
    lines.append("")
    op_count = signature.get("operator_count") or operator_report.get("operator_count") or {}
    ops = _top_ops(op_count)
    if ops:
        lines.append(_table(["算子", "数量"], ops))
    else:
        lines.append("暂无算子统计。")
    lines.append("")

    # Advice
    lines.append("## 8. 后续建议")
    lines.append("")
    advices = []
    if not preprocess:
        advices.append("补充或重新生成 `preprocess.json`，确认输入尺寸、layout、归一化方式与训练时一致。")
    if local_result and success and not label_map_path and enriched_topk:
        advices.append("为分类模型补充 `label_map.json`，使报告能够显示类别名称而不是纯 index。")
    if signature.get("has_dynamic_shape"):
        advices.append("模型包含动态 shape，后续需要在 WebUI 中允许用户填写实际输入尺寸。")
    if source_input_img:
        advices.append("PDF 报告已加入输入图片，便于检查测试样本是否正确。")
    if output_visual_img or topk_img:
        advices.append("PDF 报告已加入输出结果预览，便于检查推理结果是否符合预期。")
    if local_result and success:
        advices.append("该模型已经可以在当前 x86 Linux 环境下使用 ONNX Runtime CPU 完成本地推理。")
    if not advices:
        advices.append("当前报告未发现明显阻塞项，可继续接入 WebUI 或多框架转换流程。")
    for item in advices:
        lines.append(f"- {item}")
    lines.append("")

    report_text = "\n".join(lines).rstrip() + "\n"
    _write_text(output, report_text)

    # Always force package-local PDF regeneration.
    # The WebUI must never show a stale global YOLO PDF or an old PDF from a previous report.
    pdf_path: Optional[Path] = None
    if generate_pdf:
        target_pdf = package_dir / "report.pdf"
        try:
            if target_pdf.exists():
                target_pdf.unlink()
        except Exception:
            pass
        generated = _try_generate_pdf(output, target_pdf)
        if generated and generated.exists() and generated.stat().st_size > 0:
            # If the underlying converter returned a different path, copy it back to package/report.pdf.
            if generated.resolve() != target_pdf.resolve():
                target_pdf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(generated, target_pdf)
            pdf_path = target_pdf if target_pdf.exists() and target_pdf.stat().st_size > 0 else generated

    mirrored: Optional[Path] = None
    mirrored_pdf: Optional[Path] = None
    if mirror_to_reports:
        mirrored = Path("reports") / f"{model_name}_local_report.md"
        _write_text(mirrored, report_text)
        mirrored_pdf = Path("reports") / f"{model_name}_local_report.pdf"
        try:
            if mirrored_pdf.exists():
                mirrored_pdf.unlink()
        except Exception:
            pass
        if pdf_path and pdf_path.exists() and pdf_path.stat().st_size > 0:
            mirrored_pdf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, mirrored_pdf)
        else:
            mirrored_pdf = None

    summary = {
        "ok": True,
        "package_dir": str(package_dir),
        "model_name": model_name,
        "report": str(output),
        "pdf": str(pdf_path) if pdf_path and pdf_path.exists() else None,
        "reports_copy": str(mirrored) if mirrored else None,
        "reports_pdf_copy": str(mirrored_pdf) if mirrored_pdf else None,
        "source_input_image": str(source_input_img) if source_input_img else None,
        "output_visual_image": str(output_visual_img or topk_img) if (output_visual_img or topk_img) else None,
        "local_success": success,
        "latency_ms": latency,
        "label_map": str(label_map_path) if label_map_path else None,
    }
    return summary


__all__ = ["generate_local_package_report"]


# ==== EdgeAI package-local PDF strict override v3 ====
# This block intentionally overrides the earlier _try_generate_pdf and the default
# generate_local_package_report wrapper. It does not depend on the exact old source
# layout, so it remains stable after previous patches.

def _try_generate_pdf(md_path, pdf_path):  # type: ignore[override]
    from pathlib import Path as _Path
    from .package_pdf import markdown_to_pdf_strict as _markdown_to_pdf_strict
    md = _Path(md_path)
    pdf = _Path(pdf_path)
    html = pdf.with_suffix(".html")
    # Remove stale package PDF/HTML first. If conversion fails, no old YOLO PDF survives.
    for p in (pdf, html):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
    try:
        out = _markdown_to_pdf_strict(md_path=md, pdf_path=pdf, html_path=html)
        out = _Path(out)
        if out.exists() and out.stat().st_size > 0:
            return out
    except Exception as exc:
        print(f"[package-pdf-v3] failed: {exc}")
    return None

_EDGEAI_ORIG_GENERATE_LOCAL_PACKAGE_REPORT_V3 = generate_local_package_report

def generate_local_package_report(
    package_dir,
    output=None,
    mirror_to_reports=False,
    title=None,
    generate_pdf=True,
):
    # mirror_to_reports defaults to False now. Package reports are the single source
    # of truth: outputs/packages/<package>/report.md/html/pdf.
    return _EDGEAI_ORIG_GENERATE_LOCAL_PACKAGE_REPORT_V3(
        package_dir=package_dir,
        output=output,
        mirror_to_reports=mirror_to_reports,
        title=title,
        generate_pdf=generate_pdf,
    )
