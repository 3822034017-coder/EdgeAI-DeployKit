from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.services.paths import INPUTS_DIR, OUTPUTS_DIR, PROJECT_ROOT, REPORTS_DIR, rel

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PACKAGE_ROOT = OUTPUTS_DIR / "packages"
IMAGENET_LABEL_PATH = PROJECT_ROOT / "edgeai" / "labels" / "imagenet_classes.txt"

COCO_ZH = {
    "person": "人", "bicycle": "自行车", "car": "汽车", "motorcycle": "摩托车", "airplane": "飞机",
    "bus": "公交车", "train": "火车", "truck": "卡车", "boat": "船", "traffic light": "交通灯",
    "fire hydrant": "消防栓", "stop sign": "停止标志", "bench": "长椅", "bird": "鸟", "cat": "猫",
    "dog": "狗", "horse": "马", "sheep": "羊", "cow": "牛", "elephant": "大象", "bear": "熊",
    "zebra": "斑马", "giraffe": "长颈鹿", "backpack": "背包", "umbrella": "雨伞", "handbag": "手提包",
    "tie": "领带", "suitcase": "行李箱", "frisbee": "飞盘", "skis": "滑雪板", "snowboard": "单板滑雪板",
    "sports ball": "球", "kite": "风筝", "baseball bat": "棒球棒", "baseball glove": "棒球手套",
    "skateboard": "滑板", "surfboard": "冲浪板", "tennis racket": "网球拍", "bottle": "瓶子",
    "cup": "杯子", "fork": "叉子", "knife": "刀", "spoon": "勺子", "bowl": "碗", "banana": "香蕉",
    "apple": "苹果", "sandwich": "三明治", "orange": "橙子", "broccoli": "西兰花", "carrot": "胡萝卜",
    "pizza": "披萨", "chair": "椅子", "couch": "沙发", "potted plant": "盆栽", "bed": "床",
    "dining table": "餐桌", "tv": "电视", "laptop": "笔记本电脑", "mouse": "鼠标", "keyboard": "键盘",
    "cell phone": "手机", "book": "书", "clock": "时钟", "vase": "花瓶", "toothbrush": "牙刷",
}

# Common ImageNet translations used by the demo models. Unknown classes still display the English label.
IMAGENET_ZH = {
    "tabby": "虎斑猫", "tabby cat": "虎斑猫", "tiger cat": "虎猫", "Persian cat": "波斯猫",
    "Siamese cat": "暹罗猫", "Egyptian cat": "埃及猫", "cougar": "美洲狮", "lynx": "猞猁",
    "leopard": "豹", "snow leopard": "雪豹", "jaguar": "美洲豹", "lion": "狮子", "tiger": "老虎",
    "cheetah": "猎豹", "brown bear": "棕熊", "American black bear": "美洲黑熊", "ice bear": "北极熊",
    "sloth bear": "懒熊", "Chihuahua": "吉娃娃", "Maltese dog": "马尔济斯犬", "Pekinese": "北京犬",
    "Shih-Tzu": "西施犬", "beagle": "比格犬", "golden retriever": "金毛寻回犬",
    "Labrador retriever": "拉布拉多寻回犬", "German shepherd": "德国牧羊犬", "French bulldog": "法国斗牛犬",
    "Great Dane": "大丹犬", "Saint Bernard": "圣伯纳犬", "malamute": "阿拉斯加雪橇犬",
    "Siberian husky": "西伯利亚哈士奇", "pug": "巴哥犬", "Samoyed": "萨摩耶犬",
    "Pomeranian": "博美犬", "chow": "松狮犬", "Pembroke": "彭布罗克威尔士柯基",
    "Cardigan": "卡迪根威尔士柯基", "toy poodle": "玩具贵宾犬", "miniature poodle": "迷你贵宾犬",
    "standard poodle": "标准贵宾犬", "red fox": "赤狐", "kit fox": "敏狐", "Arctic fox": "北极狐",
    "grey fox": "灰狐", "giant panda": "大熊猫", "lesser panda": "小熊猫", "koala": "考拉",
    "wombat": "袋熊", "zebra": "斑马", "wild boar": "野猪", "panda": "熊猫",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _mtime(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except Exception:
        return None


@lru_cache(maxsize=1)
def _imagenet_labels() -> list[str]:
    if not IMAGENET_LABEL_PATH.exists():
        return []
    return [
        line.strip()
        for line in IMAGENET_LABEL_PATH.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _imagenet_label(index: Any) -> str | None:
    idx = _as_int(index)
    if idx is None:
        return None
    labels = _imagenet_labels()
    if 0 <= idx < len(labels):
        return labels[idx]
    return None


def _english_label(index: Any, model_type: Any) -> str | None:
    idx = _as_int(index)
    if idx is None:
        return None
    kind = str(model_type or "").lower()
    if kind == "mnist":
        return str(idx)
    if kind in {"mobilenetv2", "resnet18"}:
        return _imagenet_label(idx)
    return None


def _zh_label(label: Any) -> str | None:
    if label is None or label == "":
        return None
    text = str(label)
    return COCO_ZH.get(text) or IMAGENET_ZH.get(text) or IMAGENET_ZH.get(text.lower())


def _safe_rel_path(path_value: Any) -> str | None:
    if not path_value:
        return None
    try:
        path = Path(str(path_value)).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        resolved = path.resolve()
        roots = [OUTPUTS_DIR, REPORTS_DIR, INPUTS_DIR, PROJECT_ROOT / "photo"]
        if any(resolved == root or root in resolved.parents for root in roots):
            return rel(resolved)
    except Exception:
        return None
    return None


def _first_image(package_dir: Path) -> Path | None:
    for name in ["source_image.png", "source_image.jpg", "source_image.jpeg", "source_image.bmp", "source_image.webp"]:
        candidate = package_dir / name
        if candidate.exists():
            return candidate.resolve()
    for candidate in sorted(package_dir.iterdir() if package_dir.exists() else []):
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES and "yolo_result" not in candidate.name:
            return candidate.resolve()
    return None


def _result_image(package_dir: Path, board_result: dict[str, Any]) -> Path | None:
    annotated = board_result.get("annotated_image")
    if annotated:
        p = Path(str(annotated))
        if not p.is_absolute():
            p = package_dir / p
        if p.exists():
            return p.resolve()
    for name in ["yolo_result.jpg", "yolo_result.png", "result.jpg", "result.png"]:
        candidate = package_dir / name
        if candidate.exists():
            return candidate.resolve()
    for candidate in sorted(package_dir.glob("*yolo*.jpg")) + sorted(package_dir.glob("*det*.jpg")):
        if candidate.exists():
            return candidate.resolve()
    return None


def _enrich_top_item(item: Any, model_type: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    class_id = _first_not_none(item.get("index"), item.get("class_id"), item.get("id"), item.get("class"))
    label_en = _first_not_none(item.get("label_en"), item.get("label"), item.get("name"), _english_label(class_id, model_type))
    out = dict(item)
    out.setdefault("index", class_id)
    out.setdefault("class_id", class_id)
    out["label_en"] = label_en
    out["label"] = label_en
    out["label_zh"] = item.get("label_zh") or _zh_label(label_en)
    return out


def _classification_payload(board_result: dict[str, Any], model_type: Any) -> dict[str, Any] | None:
    top1 = _first_not_none(board_result.get("top1"), board_result.get("predict"))
    top1_label = _first_not_none(
        board_result.get("top1_label"),
        board_result.get("predict_label"),
        _english_label(top1, model_type),
    )
    raw_top5 = board_result.get("top5") or []
    top5: list[dict[str, Any]] = []
    if isinstance(raw_top5, list):
        for item in raw_top5:
            enriched = _enrich_top_item(item, model_type)
            if enriched is not None:
                top5.append(enriched)

    if top1 is None and top5:
        top1 = _first_not_none(top5[0].get("index"), top5[0].get("class_id"))
    if not top1_label and top5:
        top1_label = _first_not_none(top5[0].get("label_en"), top5[0].get("label"))

    if top1 is None and not top5:
        return None

    confidence = None
    if top5:
        confidence = _first_not_none(top5[0].get("prob"), top5[0].get("confidence"))

    return {
        "class_id": top1,
        "label_en": top1_label,
        "label_zh": _zh_label(top1_label),
        "confidence": confidence,
        "top5": top5,
    }


def _is_yolo_model(value: Any) -> bool:
    text = str(value or "").lower()
    return "yolo" in text or "yolov5" in text or "yolov8" in text


def _detections_payload(board_result: dict[str, Any]) -> list[dict[str, Any]]:
    detections = board_result.get("detections") or []
    if not isinstance(detections, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in detections:
        if not isinstance(item, dict):
            continue
        label = item.get("label") or item.get("label_en") or item.get("class")
        rows.append({
            "class_id": item.get("class_id"),
            "label_en": label,
            "label_zh": item.get("label_zh") or _zh_label(label),
            "confidence": item.get("confidence"),
            "bbox": item.get("bbox_xyxy_original") or item.get("bbox_xyxy_input") or item.get("box"),
            "raw": item,
        })
    return rows


def package_to_infer_result(package_dir: Path) -> dict[str, Any] | None:
    if not package_dir.exists() or not package_dir.is_dir():
        return None

    model_json = _read_json(package_dir / "model.json")
    board_result = _read_json(package_dir / "board_result.json")
    if not board_result:
        board_result = model_json.get("board_result") if isinstance(model_json.get("board_result"), dict) else {}

    package_result = _read_json(package_dir / "package_result.json")
    convert_result = _read_json(package_dir / "convert_result.json")
    sync_result = _read_json(package_dir / "board_sync_result.json")
    run_result = _read_json(package_dir / "board_run_result.json")

    contract = model_json.get("deployment_contract") if isinstance(model_json.get("deployment_contract"), dict) else {}
    model_type = (
        board_result.get("model_type")
        or contract.get("model_type")
        or model_json.get("model_type")
        or package_result.get("model_type")
        or package_dir.name
    )

    input_source = model_json.get("input_source") if isinstance(model_json.get("input_source"), dict) else {}
    source_input_path = _safe_rel_path(input_source.get("source"))
    source_image = _first_image(package_dir)
    result_image = _result_image(package_dir, board_result)
    detections = _detections_payload(board_result)
    prediction = _classification_payload(board_result, model_type)

    if detections or board_result.get("detection_count") is not None or result_image or _is_yolo_model(model_type) or _is_yolo_model(package_dir.name):
        result_type = "detection"
    elif prediction:
        result_type = "classification"
    else:
        result_type = "unknown"

    status = board_result.get("status") or run_result.get("status") or "not_run"

    return {
        "model": package_dir.name,
        "model_type": model_type,
        "result_type": result_type,
        "status": status,
        "package_dir": rel(package_dir),
        "source_input_path": source_input_path,
        "input_image": rel(source_image) if source_image else None,
        "result_image": rel(result_image) if result_image else None,
        "prediction": prediction,
        "detections": detections,
        "detection_count": board_result.get("detection_count") if board_result else len(detections),
        "latency_ms": board_result.get("latency_ms") or board_result.get("board_latency_ms"),
        "device": board_result.get("target") or "OrangePi AIPro",
        "runtime": board_result.get("runtime"),
        "updated_at": _mtime(package_dir / "board_result.json") or _mtime(package_dir / "model.json") or _mtime(package_dir),
        "artifacts": {
            "model_json": rel(package_dir / "model.json") if (package_dir / "model.json").exists() else None,
            "board_result": rel(package_dir / "board_result.json") if (package_dir / "board_result.json").exists() else None,
            "convert_result": rel(package_dir / "convert_result.json") if (package_dir / "convert_result.json").exists() else None,
            "board_sync_result": rel(package_dir / "board_sync_result.json") if (package_dir / "board_sync_result.json").exists() else None,
            "board_run_result": rel(package_dir / "board_run_result.json") if (package_dir / "board_run_result.json").exists() else None,
        },
        "raw": {
            "board_result": board_result,
            "model_json": model_json,
            "convert_result": convert_result,
            "board_sync_result": sync_result,
            "board_run_result": run_result,
        },
    }


def list_infer_results() -> list[dict[str, Any]]:
    if not PACKAGE_ROOT.exists():
        return []
    results = [item for path in sorted(PACKAGE_ROOT.iterdir()) if (item := package_to_infer_result(path)) is not None]
    return sorted(results, key=lambda item: item.get("updated_at") or "", reverse=True)


def get_infer_result(model_name: str) -> dict[str, Any]:
    safe = Path(model_name).name
    result = package_to_infer_result(PACKAGE_ROOT / safe)
    if result is None:
        raise HTTPException(status_code=404, detail="infer result not found")
    return result


def resolve_public_file(path: str) -> Path:
    raw = Path(path)
    candidate = raw if raw.is_absolute() else PROJECT_ROOT / raw
    resolved = candidate.resolve()
    allowed = [OUTPUTS_DIR, REPORTS_DIR, INPUTS_DIR, PROJECT_ROOT / "photo"]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        raise HTTPException(status_code=400, detail="file path is outside public roots")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return resolved
