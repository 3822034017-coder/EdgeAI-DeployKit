from __future__ import annotations

import html
import json
from pathlib import Path


MATRIX_PATH = Path("outputs/model_matrix/matrix.json")


def _load_matrix() -> list[dict]:
    if not MATRIX_PATH.exists():
        raise FileNotFoundError(
            f"Matrix not found: {MATRIX_PATH}. Run 'edgeai matrix' first."
        )
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8-sig"))


def generate_matrix_reports(
    markdown_output: Path = Path("reports/model_matrix.md"),
    html_output: Path = Path("reports/model_matrix.html"),
) -> None:
    matrix = _load_matrix()
    markdown_output = Path(markdown_output)
    html_output = Path(html_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    html_output.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "Model",
        "Type",
        "ONNX",
        "Benchmark",
        "Package",
        "OM",
        "Board",
        "PC Avg(ms)",
        "Board(ms)",
        "Result",
    ]

    markdown_lines = [
        "# EdgeAI Deploy Matrix",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]

    html_rows = []

    for item in matrix:
        result = item.get("top1_label")
        if result is None:
            result = item.get("top1")
        if result is None:
            result = item.get("detection_count")

        values = [
            item.get("model"),
            item.get("model_type"),
            item.get("onnx_check"),
            item.get("benchmark"),
            item.get("package"),
            item.get("om_convert"),
            item.get("board_run"),
            item.get("avg_latency_ms"),
            item.get("board_latency_ms"),
            result,
        ]

        markdown_lines.append(
            "| " + " | ".join("" if value is None else str(value) for value in values) + " |"
        )

        html_rows.append(
            "<tr>"
            + "".join(
                f"<td>{html.escape('' if value is None else str(value))}</td>"
                for value in values
            )
            + "</tr>"
        )

    markdown_output.write_text(
        "\n".join(markdown_lines) + "\n",
        encoding="utf-8",
    )

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>EdgeAI Deploy Matrix</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #cccccc; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>EdgeAI Deploy Matrix</h1>
  <table>
    <thead>
      <tr>{''.join(f'<th>{html.escape(name)}</th>' for name in headers)}</tr>
    </thead>
    <tbody>
      {''.join(html_rows)}
    </tbody>
  </table>
</body>
</html>
"""
    html_output.write_text(html_text, encoding="utf-8")

    print(f"Matrix Markdown report saved to: {markdown_output}")
    print(f"Matrix HTML report saved to: {html_output}")
