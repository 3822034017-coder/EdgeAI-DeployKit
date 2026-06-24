from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .label_utils import enrich_classification_labels, load_imagenet_labels


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_optional(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except Exception as exc:
        print(f"[WARN] skip broken json {path}: {exc}")
        return None


def _status(value: Any, default: str = "NOT_RUN") -> str:
    if value is None:
        return default
    text = str(value).upper()
    if text == "SUCCESS":
        return "PASS"
    if text == "FAILED":
        return "FAIL"
    return text


def _new_record(name: str) -> dict[str, Any]:
    return {
        "model": name,
        "model_type": None,
        "package_dir": None,
        "onnx_check": "NOT_RUN",
        "benchmark": "NOT_RUN",
        "package": "NOT_RUN",
        "board_sync": "NOT_RUN",
        "om_convert": "NOT_RUN",
        "board_run": "NOT_RUN",
        "input_name": None,
        "input_shape": None,
        "input_dtype": None,
        "input_format": None,
        "input_file": None,
        "input_type": None,
        "avg_latency_ms": None,
        "p50_ms": None,
        "p95_ms": None,
        "min_ms": None,
        "max_ms": None,
        "board_latency_ms": None,
        "top1": None,
        "top1_label": None,
        "predict": None,
        "predict_label": None,
        "top5": None,
        "detection_count": None,
        "detections": None,
        "annotated_image": None,
        "board_output_count": None,
    }


def _merge_benchmark(record: dict[str, Any], benchmark_root: Path) -> None:
    names = [
        record["model"],
        record.get("model_type"),
    ]
    bench_fields_latency = ["avg_latency_ms", "p50_ms", "p95_ms", "min_ms", "max_ms"]
    bench_fields_meta = [
        "input_file", "input_type", "model_type",
        "predict", "predict_label", "top5",
        "detection_count", "detections", "annotated_image",
    ]
    for name in names:
        if not name:
            continue
        bench = _read_optional(benchmark_root / f"{name}.json")
        if not bench:
            continue
        record["benchmark"] = "PASS"
        for key in bench_fields_latency + bench_fields_meta:
            if bench.get(key) is not None:
                record[key] = bench[key]
        return


def _merge_model_json(record: dict[str, Any], data: dict[str, Any]) -> None:
    contract = data.get("deployment_contract") or {}
    board = data.get("board") or {}
    board_result = data.get("board_result") or {}

    record["model_type"] = contract.get("model_type") or data.get("model_type") or record.get("model_type")
    record["input_name"] = contract.get("input_name") or data.get("input_name")
    record["input_shape"] = contract.get("input_shape") or data.get("input_shape")
    record["input_dtype"] = contract.get("input_dtype") or data.get("input_dtype")
    record["input_format"] = contract.get("input_format") or data.get("input_format")

    if board.get("om_convert"):
        record["om_convert"] = _status(board.get("om_convert"))
    if board_result:
        _merge_board_result(record, board_result)


def _merge_board_result(record: dict[str, Any], board: dict[str, Any]) -> None:
    record["board_run"] = _status(board.get("status"), record["board_run"])
    record["board_latency_ms"] = board.get("latency_ms") or board.get("board_latency_ms")
    record["top1"] = board.get("top1")
    record["top1_label"] = board.get("top1_label")
    record["predict"] = board.get("predict") or board.get("top1")
    record["predict_label"] = board.get("predict_label") or board.get("top1_label")
    record["top5"] = board.get("top5")
    record["detection_count"] = board.get("detection_count")
    record["detections"] = board.get("detections")
    record["annotated_image"] = board.get("annotated_image") or record.get("annotated_image")
    record["board_output_count"] = board.get("output_count")
    # track input_file from board result as well (if not already from benchmark)
    if board.get("source_image") and not record.get("input_file"):
        record["input_file"] = board["source_image"]
        record["input_type"] = "image"
    labels = load_imagenet_labels()
    enrich_classification_labels(record, record.get("model_type"), labels)


def _write_labeled_board_result(package_dir: Path, board: dict[str, Any], model_type: Any) -> None:
    labels = load_imagenet_labels()
    if enrich_classification_labels(board, model_type, labels):
        (package_dir / "board_result.json").write_text(
            json.dumps(board, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _record_from_package(package_dir: Path, benchmark_root: Path) -> dict[str, Any]:
    record = _new_record(package_dir.name)
    record["package_dir"] = str(package_dir)

    package_result = _read_optional(package_dir / "package_result.json")
    if package_result:
        record["package"] = _status(package_result.get("package") or package_result.get("status"))
        record["model_type"] = package_result.get("model_type") or record["model_type"]
        for key in ["input_name", "input_shape", "input_dtype", "input_format"]:
            record[key] = package_result.get(key, record[key])

    model_json = _read_optional(package_dir / "model.json")
    if model_json:
        _merge_model_json(record, model_json)

    sync_result = _read_optional(package_dir / "board_sync_result.json")
    if sync_result:
        record["board_sync"] = _status(sync_result.get("status"))

    convert_result = _read_optional(package_dir / "convert_result.json")
    if convert_result:
        record["om_convert"] = _status(convert_result.get("status"))

    board_run_result = _read_optional(package_dir / "board_run_result.json")
    if board_run_result:
        record["board_run"] = _status(board_run_result.get("status"))

    _merge_benchmark(record, benchmark_root)

    board_result = _read_optional(package_dir / "board_result.json")
    if board_result:
        _write_labeled_board_result(package_dir, board_result, record.get("model_type"))
        _merge_board_result(record, board_result)
    return record


def _record_from_old_deploy(model_dir: Path, benchmark_root: Path, board_root: Path) -> dict[str, Any]:
    record = _new_record(model_dir.name)
    deploy_file = model_dir / "deploy_result.json"
    deploy_data = _read_optional(deploy_file)
    if deploy_data:
        for key in ["onnx_check", "package", "om_convert", "board_run"]:
            record[key] = deploy_data.get(key, record[key])

    board_file = board_root / f"{model_dir.name}.json"
    board_data = _read_optional(board_file)
    if board_data:
        _merge_board_result(record, board_data)

    _merge_benchmark(record, benchmark_root)
    return record


def generate_matrix():
    package_root = Path("outputs/packages")
    deploy_root = Path("outputs/deploy")
    benchmark_root = Path("outputs/benchmark")
    board_root = Path("outputs/board_result")

    matrix = []
    seen = set()

    if package_root.exists():
        for package_dir in sorted(package_root.iterdir()):
            if not package_dir.is_dir():
                continue
            record = _record_from_package(package_dir, benchmark_root)
            matrix.append(record)
            seen.add(record["model"])

    if deploy_root.exists():
        for model_dir in sorted(deploy_root.iterdir()):
            if not model_dir.is_dir() or model_dir.name in seen:
                continue
            matrix.append(_record_from_old_deploy(model_dir, benchmark_root, board_root))

    if not matrix:
        print("No package/deploy result found.")
        return

    output_dir = Path("outputs/model_matrix")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "matrix.json"
    output_file.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"Matrix saved -> {output_file}")
    print()
    print(json.dumps(matrix, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    generate_matrix()
