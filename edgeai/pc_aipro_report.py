from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _positive_number(value: Any):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def compare_item(item: dict) -> dict:
    pc = _positive_number(item.get("avg_latency_ms"))
    aipro = _positive_number(item.get("board_latency_ms"))

    prediction = item.get("top1_label")
    if prediction is None:
        prediction = item.get("top1")
    if prediction is None and item.get("detection_count") is not None:
        prediction = f"detections={item['detection_count']}"

    result = {
        "model": item.get("model", ""),
        "model_type": item.get("model_type", ""),
        "pc_status": item.get("benchmark", "NOT_RUN"),
        "aipro_status": item.get("board_run", "NOT_RUN"),
        "pc_ms": pc,
        "aipro_ms": aipro,
        "difference_ms": None,
        "relative_speed": None,
        "change_percent": None,
        "conclusion": "NOT_RUN",
        "prediction": prediction,
    }

    if pc is None or aipro is None:
        return result

    result["difference_ms"] = aipro - pc
    result["relative_speed"] = pc / aipro
    result["change_percent"] = (pc - aipro) / pc * 100

    if result["change_percent"] > 5:
        result["conclusion"] = "AIPro faster"
    elif result["change_percent"] < -5:
        result["conclusion"] = "PC faster"
    else:
        result["conclusion"] = "Similar"

    return result


def _fmt(value, digits=4, suffix=""):
    if value is None:
        return "NOT_RUN"
    return f"{value:.{digits}f}{suffix}"


def generate_pc_aipro_reports(
    matrix_path: Path = Path("outputs/model_matrix/matrix.json"),
    markdown_output: Path = Path("reports/pc_aipro_compare.md"),
    html_output: Path = Path("reports/pc_aipro_compare.html"),
) -> None:
    matrix_path = Path(matrix_path)
    if not matrix_path.exists():
        raise FileNotFoundError(
            f"Matrix not found: {matrix_path}. Run 'edgeai matrix' first."
        )

    matrix = json.loads(matrix_path.read_text(encoding="utf-8-sig"))
    if not isinstance(matrix, list):
        raise ValueError("Matrix JSON root must be a list.")

    rows = [compare_item(item) for item in matrix]
    comparable = [row for row in rows if row["conclusion"] != "NOT_RUN"]

    summary = {
        "Total Models": len(rows),
        "Comparable Models": len(comparable),
        "AIPro Faster": sum(r["conclusion"] == "AIPro faster" for r in rows),
        "PC Faster": sum(r["conclusion"] == "PC faster" for r in rows),
        "Similar": sum(r["conclusion"] == "Similar" for r in rows),
        "Not Run": sum(r["conclusion"] == "NOT_RUN" for r in rows),
    }

    headers = [
        "Model", "Type", "PC Status", "AIPro Status",
        "PC Avg(ms)", "AIPro(ms)", "Difference(ms)",
        "AIPro Relative Speed", "AIPro Change(%)",
        "Result", "Prediction",
    ]

    table_rows = []
    for row in rows:
        table_rows.append([
            row["model"],
            row["model_type"],
            row["pc_status"],
            row["aipro_status"],
            _fmt(row["pc_ms"]),
            _fmt(row["aipro_ms"]),
            _fmt(row["difference_ms"]),
            _fmt(row["relative_speed"], 2, "x"),
            _fmt(row["change_percent"], 2, "%"),
            row["conclusion"],
            "" if row["prediction"] is None else row["prediction"],
        ])

    markdown_lines = [
        "# PC vs OrangePi AIPro Inference Comparison",
        "",
        "This report compares inference latency only. Model conversion,",
        "file transfer, preprocessing and service startup are excluded.",
        "",
        "## Summary",
        "",
    ]
    markdown_lines.extend(f"- {key}: {value}" for key, value in summary.items())
    markdown_lines.extend([
        "",
        "## Comparison",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ])
    markdown_lines.extend(
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in table_rows
    )

    markdown_output = Path(markdown_output)
    html_output = Path(html_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    html_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    html_headers = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    html_rows = "".join(
        "<tr>" + "".join(
            f"<td>{html.escape(str(value))}</td>" for value in row
        ) + "</tr>"
        for row in table_rows
    )
    html_summary = "".join(
        f"<li>{html.escape(key)}: {value}</li>"
        for key, value in summary.items()
    )

    html_output.write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PC vs OrangePi AIPro Comparison</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:8px;text-align:left}}
th{{background:#f3f4f6}}
</style>
</head>
<body>
<h1>PC vs OrangePi AIPro Inference Comparison</h1>
<p>Inference latency only. Conversion, transfer and preprocessing are excluded.</p>
<h2>Summary</h2><ul>{html_summary}</ul>
<h2>Comparison</h2>
<table><thead><tr>{html_headers}</tr></thead>
<tbody>{html_rows}</tbody></table>
</body>
</html>
""", encoding="utf-8")

    print(f"PC/AIPro Markdown report saved to: {markdown_output}")
    print(f"PC/AIPro HTML report saved to: {html_output}")
