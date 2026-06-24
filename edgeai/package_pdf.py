from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def _inline_markdown(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def _markdown_to_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    base = md_path.parent.resolve()
    out: list[str] = []
    in_table = False
    in_ul = False
    in_code = False
    code_lines: list[str] = []

    def close_table() -> None:
        nonlocal in_table
        if in_table:
            out.append("</tbody></table>")
            in_table = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def close_code() -> None:
        nonlocal in_code, code_lines
        if in_code:
            out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
            in_code = False
            code_lines = []

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            close_table(); close_ul()
            if in_code:
                close_code()
            else:
                in_code = True
                code_lines = []
            continue
        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            close_table(); close_ul()
            out.append('<div class="spacer"></div>')
            continue

        m_img = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if m_img:
            close_table(); close_ul()
            alt = html.escape(m_img.group(1))
            src = m_img.group(2).strip()
            src_path = Path(src)
            if not src_path.is_absolute():
                src_path = (base / src_path).resolve()
            if src_path.exists():
                out.append(f'<figure><img src="{src_path.as_uri()}" alt="{alt}"/><figcaption>{alt}</figcaption></figure>')
            else:
                out.append(f'<p class="missing-image">Image not found: {html.escape(src)}</p>')
            continue

        if stripped == "---":
            close_table(); close_ul(); out.append("<hr/>"); continue
        if stripped.startswith("# "):
            close_table(); close_ul(); out.append(f"<h1>{_inline_markdown(stripped[2:].strip())}</h1>"); continue
        if stripped.startswith("## "):
            close_table(); close_ul(); out.append(f"<h2>{_inline_markdown(stripped[3:].strip())}</h2>"); continue
        if stripped.startswith("### "):
            close_table(); close_ul(); out.append(f"<h3>{_inline_markdown(stripped[4:].strip())}</h3>"); continue
        if stripped.startswith("#### "):
            close_table(); close_ul(); out.append(f"<h4>{_inline_markdown(stripped[5:].strip())}</h4>"); continue
        if stripped.startswith(">"):
            close_table(); close_ul(); out.append(f"<blockquote>{_inline_markdown(stripped[1:].strip())}</blockquote>"); continue
        if stripped.startswith("- "):
            close_table()
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{_inline_markdown(stripped[2:].strip())}</li>")
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            close_ul()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
                continue
            if not in_table:
                out.append("<table><tbody>"); in_table = True
                tag = "th"
            else:
                tag = "td"
            row = "".join(f"<{tag}>{_inline_markdown(c)}</{tag}>" for c in cells)
            out.append(f"<tr>{row}</tr>")
            continue

        close_table(); close_ul()
        out.append(f"<p>{_inline_markdown(stripped)}</p>")

    close_code(); close_table(); close_ul()
    body = "\n".join(out)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>{html.escape(md_path.stem)}</title>
<style>
@page {{ size: A4; margin: 18mm 16mm; }}
body {{ font-family: 'Noto Sans CJK SC','Noto Sans SC','Microsoft YaHei','PingFang SC','DejaVu Sans',sans-serif; color:#0f172a; line-height:1.72; font-size:12.5px; }}
h1 {{ font-size:24px; margin:0 0 14px; color:#0f172a; }}
h2 {{ font-size:18px; margin:24px 0 10px; color:#111827; border-bottom:1px solid #e5e7eb; padding-bottom:5px; }}
h3 {{ font-size:15px; margin:18px 0 8px; color:#1f2937; }}
h4 {{ font-size:13.5px; margin:14px 0 6px; color:#334155; }}
p {{ margin:7px 0; }}
blockquote {{ margin:10px 0; padding:8px 12px; background:#f8fafc; border-left:4px solid #38bdf8; color:#334155; }}
code {{ background:#f1f5f9; padding:1px 4px; border-radius:4px; font-family:'DejaVu Sans Mono',monospace; font-size:11px; }}
pre {{ background:#0f172a; color:#e5eefc; padding:10px 12px; border-radius:8px; white-space:pre-wrap; word-break:break-word; }}
pre code {{ background:transparent; color:inherit; padding:0; }}
table {{ width:100%; border-collapse:collapse; margin:10px 0 16px; page-break-inside:avoid; }}
th, td {{ border:1px solid #dbe3ef; padding:6px 8px; text-align:left; vertical-align:top; word-break:break-word; }}
th {{ background:#edf2f7; font-weight:700; }}
tr:nth-child(even) td {{ background:#fbfdff; }}
ul {{ margin:6px 0 10px 20px; padding:0; }}
figure {{ margin:12px 0 18px; page-break-inside:avoid; }}
img {{ max-width:100%; height:auto; border:1px solid #e5e7eb; border-radius:8px; }}
figcaption {{ color:#64748b; font-size:11px; margin-top:4px; }}
hr {{ border:none; border-top:1px solid #e5e7eb; margin:18px 0; }}
.spacer {{ height:4px; }}
.missing-image {{ color:#b91c1c; background:#fef2f2; padding:8px; border-radius:6px; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _reportlab_font_candidates() -> list[Path]:
    return [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Regular.otf"),
        Path("/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/google-droid-fonts/DroidSansFallback.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    ]


def _register_reportlab_font() -> str:
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception:
        return "Helvetica"

    for path in _reportlab_font_candidates():
        if not path.exists():
            continue
        try:
            name = "EdgeAICJK"
            if path.suffix.lower() == ".ttc":
                try:
                    pdfmetrics.registerFont(TTFont(name, str(path), subfontIndex=0))
                except TypeError:
                    pdfmetrics.registerFont(TTFont(name, str(path)))
            else:
                pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
        except Exception:
            continue
    return "Helvetica"


def _markdown_to_pdf_reportlab(md_path: Path, pdf_path: Path) -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Image, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        raise RuntimeError("reportlab is not installed") from exc

    base = md_path.parent.resolve()
    text = md_path.read_text(encoding="utf-8", errors="replace")
    font_name = _register_reportlab_font()
    code_font = font_name if font_name != "Helvetica" else "Courier"

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "EdgeAIBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=5,
    )
    h1 = ParagraphStyle("EdgeAIH1", parent=body, fontSize=17, leading=22, spaceAfter=10)
    h2 = ParagraphStyle("EdgeAIH2", parent=body, fontSize=13.5, leading=18, spaceBefore=10, spaceAfter=7)
    h3 = ParagraphStyle("EdgeAIH3", parent=body, fontSize=11.5, leading=15, spaceBefore=7, spaceAfter=5)
    quote = ParagraphStyle(
        "EdgeAIQuote",
        parent=body,
        leftIndent=8,
        borderColor=colors.HexColor("#38bdf8"),
        borderWidth=1,
        borderPadding=5,
        backColor=colors.HexColor("#f8fafc"),
    )
    code = ParagraphStyle(
        "EdgeAICode",
        parent=body,
        fontName=code_font,
        fontSize=7.5,
        leading=10,
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=4,
    )

    def paragraph(value: str, style: ParagraphStyle = body) -> Paragraph:
        escaped = html.escape(value)
        escaped = re.sub(r"`([^`]+)`", lambda m: f'<font name="{code_font}">{m.group(1)}</font>', escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
        return Paragraph(escaped, style)

    def image_flowable(src: str, alt: str):
        src_path = Path(src.strip())
        if not src_path.is_absolute():
            src_path = (base / src_path).resolve()
        if not src_path.exists():
            return paragraph(f"Image not found: {src}", quote)
        img = Image(str(src_path))
        max_w = A4[0] - 40 * mm
        max_h = A4[1] - 70 * mm
        scale = min(max_w / max(img.imageWidth, 1), max_h / max(img.imageHeight, 1), 1.0)
        img.drawWidth = img.imageWidth * scale
        img.drawHeight = img.imageHeight * scale
        return [img, paragraph(alt, body), Spacer(1, 5)]

    def flush_table(rows: list[list[str]], story: list) -> None:
        if not rows:
            return
        col_count = max(len(r) for r in rows)
        normalized = [r + [""] * (col_count - len(r)) for r in rows]
        data = [[paragraph(cell, body) for cell in row] for row in normalized]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dbe3ef")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 7))

    story: list = []
    table_rows: list[list[str]] = []
    in_code = False
    code_lines: list[str] = []

    def close_code() -> None:
        nonlocal in_code, code_lines
        if in_code:
            story.append(Preformatted("\n".join(code_lines), code))
            story.append(Spacer(1, 5))
            in_code = False
            code_lines = []

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_table(table_rows, story); table_rows = []
            if in_code:
                close_code()
            else:
                in_code = True
                code_lines = []
            continue
        if in_code:
            code_lines.append(line)
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
                continue
            table_rows.append(cells)
            continue

        flush_table(table_rows, story); table_rows = []

        if not stripped:
            story.append(Spacer(1, 4))
            continue
        match_img = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if match_img:
            flow = image_flowable(match_img.group(2), match_img.group(1))
            if isinstance(flow, list):
                story.extend(flow)
            else:
                story.append(flow)
            continue
        if stripped == "---":
            story.append(Spacer(1, 8))
            continue
        if stripped.startswith("# "):
            story.append(paragraph(stripped[2:].strip(), h1))
        elif stripped.startswith("## "):
            story.append(paragraph(stripped[3:].strip(), h2))
        elif stripped.startswith("### "):
            story.append(paragraph(stripped[4:].strip(), h3))
        elif stripped.startswith(">"):
            story.append(paragraph(stripped[1:].strip(), quote))
        elif stripped.startswith("- "):
            story.append(paragraph("- " + stripped[2:].strip(), body))
        else:
            story.append(paragraph(stripped, body))

    close_code()
    flush_table(table_rows, story)

    if not story:
        story.append(paragraph(md_path.name, body))

    tmp_path = pdf_path.with_suffix(pdf_path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    doc = SimpleDocTemplate(
        str(tmp_path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=md_path.stem,
    )
    doc.build(story)
    tmp_path.replace(pdf_path)
    return pdf_path


def markdown_to_pdf_strict(md_path: Path, pdf_path: Path, html_path: Optional[Path] = None) -> Path:
    md_path = Path(md_path).expanduser().resolve()
    pdf_path = Path(pdf_path).expanduser().resolve()
    html_path = Path(html_path).expanduser().resolve() if html_path else pdf_path.with_suffix(".html")

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown not found: {md_path}")

    # Refuse global stale report paths unless explicitly forced.
    joined = f"{md_path}\n{pdf_path}\n{html_path}"
    if "reports/edgeai_report" in joined:
        raise RuntimeError("Legacy global reports/edgeai_report.* is disabled for package reports")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)

    if pdf_path.exists():
        pdf_path.unlink()

    html_path.write_text(_markdown_to_html(md_path), encoding="utf-8")

    try:
        from weasyprint import HTML
        HTML(filename=str(html_path), base_url=str(md_path.parent.resolve())).write_pdf(str(pdf_path))
    except Exception as weasy_exc:
        if shutil.which("pandoc"):
            try:
                subprocess.run([
                    "pandoc", str(md_path), "-o", str(pdf_path),
                    "--resource-path", str(md_path.parent.resolve()),
                    "-V", "geometry:margin=2cm",
                ], check=True, timeout=60)
            except Exception:
                pass
        if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
            try:
                _markdown_to_pdf_reportlab(md_path, pdf_path)
            except Exception as reportlab_exc:
                raise RuntimeError(
                    "failed to create package-local PDF with weasyprint, pandoc, and reportlab: "
                    + repr(reportlab_exc)
                ) from weasy_exc

    if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
        raise RuntimeError(f"PDF was not created: {pdf_path}")
    return pdf_path
