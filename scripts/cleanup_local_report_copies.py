from pathlib import Path

root = Path(__file__).resolve().parents[1]
reports = root / "reports"
patterns = ["*_local_report.md", "*_local_report.pdf"]
removed = []
for pattern in patterns:
    for path in reports.glob(pattern):
        # Keep board/global edgeai_report.* untouched.
        try:
            path.unlink()
            removed.append(path.relative_to(root).as_posix())
        except Exception as exc:
            print(f"[WARN] failed to remove {path}: {exc}")
print({"removed": removed, "count": len(removed)})
