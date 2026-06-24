#!/usr/bin/env python3
"""Generic board-side runner for airloader.

No cv2 dependency. It reads model JSON + input.npy, sends raw tensor bytes to
airloader, then writes board_result.json and optionally updates the model JSON.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Optional

import numpy as np

from json_contract import load_json, normalize_contract, save_json


COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]


def dtype_to_numpy(dtype: str):
    mapping = {
        "float32": np.float32,
        "float64": np.float64,
        "int64": np.int64,
        "int32": np.int32,
        "uint8": np.uint8,
    }
    return mapping.get(dtype.lower(), np.float32)


class GenericRemoteRunner:
    def __init__(self, remote: str, port: int, tensor: np.ndarray, output_dtype: str):
        from inferemote.atlas_remote import AtlasRemote

        class _Remote(AtlasRemote):
            def __init__(self, outer: "GenericRemoteRunner"):
                self.outer = outer
                self.last_outputs = None
                super().__init__(remote=outer.remote, port=outer.port)

            def pre_process(self, _unused):
                return self.outer.tensor.tobytes()

            def post_process(self, result):
                if not result:
                    raise RuntimeError("empty airloader result")
                dtype = dtype_to_numpy(self.outer.output_dtype)
                self.last_outputs = [np.frombuffer(item, dtype) for item in result]
                return self.last_outputs

        self.remote = remote
        self.port = port
        self.tensor = tensor
        self.output_dtype = output_dtype
        self.client = _Remote(self)

    def run(self, source: str = "input.npy"):
        result = self.client.inference_remote(source)
        if result is None:
            raise RuntimeError("no result returned from airloader")
        return self.client.last_outputs


def _positive_shape(shape) -> list[int]:
    if not isinstance(shape, list):
        return []
    values = []
    for item in shape:
        try:
            value = int(item)
        except (TypeError, ValueError):
            return []
        if value <= 0:
            return []
        values.append(value)
    return values


def reshape_outputs(outputs: list[np.ndarray], contract: dict) -> list[np.ndarray]:
    shaped = []
    output_meta = contract.get("outputs") or []
    for idx, output in enumerate(outputs):
        arr = output
        if idx < len(output_meta):
            shape = _positive_shape(output_meta[idx].get("shape"))
            if shape and int(np.prod(shape)) == arr.size:
                arr = arr.reshape(shape)
        if contract["model_type"] == "yolov5n" and arr.ndim == 1 and arr.size % 85 == 0:
            arr = arr.reshape(1, arr.size // 85, 85)
        shaped.append(arr)
    return shaped


def summarize_outputs(outputs: list[np.ndarray]) -> list[dict]:
    summaries = []
    for idx, output in enumerate(outputs):
        flat = output.flatten()
        summaries.append(
            {
                "index": idx,
                "dtype": str(output.dtype),
                "size": int(output.size),
                "shape": list(output.shape),
                "sample": [float(x) for x in flat[:10]],
            }
        )
    return summaries


def maybe_classification(outputs: list[np.ndarray], model_type: str) -> dict:
    if not outputs:
        return {}
    if model_type not in {"mnist", "mobilenetv2", "resnet18"}:
        return {}
    values = outputs[0].astype(np.float32).flatten()
    if values.size < 2:
        return {}
    shifted = values - values.max()
    probs = np.exp(shifted) / np.exp(shifted).sum()
    top = probs.argsort()[-1:-6:-1]
    return {
        "top1": int(top[0]),
        "top5": [
            {"index": int(idx), "prob": float(probs[idx])}
            for idx in top
        ],
    }


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values.astype(np.float32), -80.0, 80.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _probability(values: np.ndarray) -> np.ndarray:
    if values.size and (float(values.min()) < 0.0 or float(values.max()) > 1.0):
        return _sigmoid(values)
    return values.astype(np.float32)


def _input_hw(contract: dict) -> tuple[int, int]:
    shape = contract["input_shape"]
    layout = contract["input_format"].upper()
    if len(shape) != 4:
        return 1, 1
    if layout == "NHWC":
        return int(shape[1]), int(shape[2])
    return int(shape[2]), int(shape[3])


def _xywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    xyxy = np.empty_like(boxes, dtype=np.float32)
    xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.0
    xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.0
    xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.0
    xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.0
    return xyxy


def _box_iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    area1 = max(0.0, float(box[2] - box[0])) * max(0.0, float(box[3] - box[1]))
    area2 = np.maximum(0.0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0.0, boxes[:, 3] - boxes[:, 1])
    return inter / np.maximum(area1 + area2 - inter, 1e-6)


def _nms(boxes: np.ndarray, scores: np.ndarray, class_ids: np.ndarray, iou_thres: float, max_det: int) -> list[int]:
    keep = []
    for class_id in np.unique(class_ids):
        indexes = np.where(class_ids == class_id)[0]
        order = indexes[np.argsort(scores[indexes])[::-1]]
        while order.size and len(keep) < max_det:
            current = int(order[0])
            keep.append(current)
            if order.size == 1:
                break
            ious = _box_iou(boxes[current], boxes[order[1:]])
            order = order[1:][ious <= iou_thres]
    keep.sort(key=lambda index: float(scores[index]), reverse=True)
    return keep[:max_det]


def _find_source_image(json_path: Path, raw: dict, explicit: Optional[str]) -> Optional[Path]:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        return path if path.exists() else None

    input_source = raw.get("input_source") or {}
    source_file = input_source.get("source_file")
    if source_file:
        path = (json_path.parent / source_file).resolve()
        if path.exists():
            return path

    for suffix in ("jpg", "jpeg", "png", "bmp", "webp"):
        matches = sorted(json_path.parent.glob(f"source_image.{suffix}"))
        if matches:
            return matches[0].resolve()
    return None


def _source_size(source_image: Optional[Path]) -> Optional[tuple[int, int]]:
    if not source_image:
        return None
    try:
        from PIL import Image

        with Image.open(source_image) as image:
            return image.size
    except Exception:
        return None


def _draw_detections(source_image: Path, detections: list[dict], output_path: Path) -> Optional[str]:
    try:
        from PIL import Image, ImageDraw

        image = Image.open(source_image).convert("RGB")
        draw = ImageDraw.Draw(image)
        for item in detections:
            box = item.get("bbox_xyxy_original") or item.get("bbox_xyxy_input")
            if not box:
                continue
            class_id = int(item["class_id"])
            color = (
                int((37 * class_id + 23) % 255),
                int((17 * class_id + 113) % 255),
                int((29 * class_id + 71) % 255),
            )
            label = f"{item['label']} {item['confidence']:.2f}"
            draw.rectangle(box, outline=color, width=3)
            left, top = box[0], max(0, box[1] - 14)
            draw.rectangle([left, top, left + max(60, 7 * len(label)), top + 14], fill=color)
            draw.text((left + 2, top + 1), label, fill=(255, 255, 255))
        image.save(output_path)
        return str(output_path)
    except Exception as exc:
        print(f"[WARN] could not draw detections: {exc}")
        return None


def maybe_yolo_detection(
    outputs: list[np.ndarray],
    contract: dict,
    source_image: Optional[Path],
    conf_thres: float,
    iou_thres: float,
    max_det: int,
    annotated_output: Optional[Path],
) -> dict:
    if contract["model_type"] != "yolov5n" or not outputs:
        return {}

    pred = outputs[0].astype(np.float32)
    if pred.ndim == 3:
        pred = pred[0]
    if pred.ndim == 2 and pred.shape[0] == 85 and pred.shape[1] != 85:
        pred = pred.T
    if pred.ndim != 2 or pred.shape[1] < 6:
        return {
            "detection_count": 0,
            "detections": [],
            "yolo": {"error": f"unsupported output shape {list(outputs[0].shape)}"},
        }

    input_h, input_w = _input_hw(contract)
    boxes = _xywh_to_xyxy(pred[:, :4])
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, input_w)
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, input_h)

    objectness = _probability(pred[:, 4])
    class_scores = _probability(pred[:, 5:])
    class_ids = class_scores.argmax(axis=1)
    class_conf = class_scores[np.arange(class_scores.shape[0]), class_ids]
    scores = objectness * class_conf
    valid = scores >= conf_thres

    if not np.any(valid):
        return {
            "detection_count": 0,
            "detections": [],
            "yolo": {
                "output_shape": list(outputs[0].shape),
                "candidate_count": int(pred.shape[0]),
                "conf_thres": conf_thres,
                "iou_thres": iou_thres,
            },
        }

    boxes = boxes[valid]
    scores = scores[valid]
    objectness = objectness[valid]
    class_conf = class_conf[valid]
    class_ids = class_ids[valid]
    keep = _nms(boxes, scores, class_ids, iou_thres, max_det)
    source_wh = _source_size(source_image)
    scale_x = source_wh[0] / input_w if source_wh else 1.0
    scale_y = source_wh[1] / input_h if source_wh else 1.0

    detections = []
    for index in keep:
        class_id = int(class_ids[index])
        box = boxes[index]
        original_box = [
            int(round(float(box[0]) * scale_x)),
            int(round(float(box[1]) * scale_y)),
            int(round(float(box[2]) * scale_x)),
            int(round(float(box[3]) * scale_y)),
        ] if source_wh else None
        detections.append(
            {
                "class_id": class_id,
                "label": COCO_CLASSES[class_id] if class_id < len(COCO_CLASSES) else f"class_{class_id}",
                "confidence": float(scores[index]),
                "objectness": float(objectness[index]),
                "class_confidence": float(class_conf[index]),
                "bbox_xyxy_input": [float(x) for x in box],
                "bbox_xywh_input": [
                    float((box[0] + box[2]) / 2.0),
                    float((box[1] + box[3]) / 2.0),
                    float(box[2] - box[0]),
                    float(box[3] - box[1]),
                ],
                "bbox_xyxy_original": original_box,
            }
        )

    annotated_image = None
    if source_image and annotated_output:
        annotated_image = _draw_detections(source_image, detections, annotated_output)

    return {
        "detection_count": len(detections),
        "detections": detections,
        "annotated_image": annotated_image,
        "yolo": {
            "output_shape": list(outputs[0].shape),
            "candidate_count": int(pred.shape[0]),
            "conf_thres": conf_thres,
            "iou_thres": iou_thres,
            "max_det": max_det,
            "input_image_size": [input_w, input_h],
            "source_image": str(source_image) if source_image else None,
            "source_image_size": list(source_wh) if source_wh else None,
        },
    }


def build_result(
    contract: dict,
    tensor: np.ndarray,
    outputs: list[np.ndarray],
    latency_ms: float,
    source_image: Optional[Path],
    conf_thres: float,
    iou_thres: float,
    max_det: int,
    annotated_output: Optional[Path],
) -> dict:
    result = {
        "status": "success",
        "target": "OrangePi AIPro",
        "runtime": "airloader",
        "model_type": contract["model_type"],
        "input_name": contract["input_name"],
        "input_shape": list(tensor.shape),
        "input_dtype": str(tensor.dtype),
        "input_bytes": int(tensor.nbytes),
        "output_count": len(outputs),
        "outputs": summarize_outputs(outputs),
        "latency_ms": latency_ms,
    }
    result.update(maybe_classification(outputs, contract["model_type"]))
    result.update(
        maybe_yolo_detection(
            outputs=outputs,
            contract=contract,
            source_image=source_image,
            conf_thres=conf_thres,
            iou_thres=iou_thres,
            max_det=max_det,
            annotated_output=annotated_output,
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic airloader runner from JSON + input.npy.")
    parser.add_argument("--json", default="model.json", help="model JSON from B/package step")
    parser.add_argument("--input", default="input.npy", help="pre-generated input tensor")
    parser.add_argument("-r", "--remote", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, default=7891)
    parser.add_argument("-w", "--wait", type=float, default=3.0)
    parser.add_argument("-o", "--output", default="board_result.json")
    parser.add_argument("--update-json", action="store_true", help="write board_result into --json file")
    parser.add_argument("--output-dtype", default="float32", help="dtype used to decode airloader output")
    parser.add_argument("--source-image", help="optional original image for YOLO box scaling/drawing")
    parser.add_argument("--conf-thres", type=float, default=0.25, help="YOLO confidence threshold")
    parser.add_argument("--iou-thres", type=float, default=0.45, help="YOLO NMS IoU threshold")
    parser.add_argument("--max-det", type=int, default=20, help="maximum YOLO detections to keep")
    parser.add_argument("--annotated-output", default="yolo_result.jpg", help="YOLO annotated image output")
    parser.add_argument("--no-annotated", action="store_true", help="disable YOLO annotated image generation")
    args = parser.parse_args()

    json_path = Path(args.json).expanduser().resolve()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not json_path.exists():
        raise SystemExit(f"[FAIL] JSON not found: {json_path}")
    if not input_path.exists():
        raise SystemExit(f"[FAIL] input tensor not found: {input_path}")

    raw_json = load_json(json_path)
    contract = normalize_contract(raw_json)
    tensor = np.load(input_path)
    expected_shape = contract["input_shape"]
    if list(tensor.shape) != expected_shape:
        print(f"[WARN] input.npy shape {list(tensor.shape)} != JSON shape {expected_shape}")

    expected_dtype = dtype_to_numpy(contract["input_dtype"])
    if tensor.dtype != expected_dtype:
        tensor = tensor.astype(expected_dtype)

    print(f"[INFO] model_type={contract['model_type']}")
    print(f"[INFO] input_name={contract['input_name']}")
    print(f"[INFO] tensor shape={list(tensor.shape)} dtype={tensor.dtype} bytes={tensor.nbytes}")
    print(f"[INFO] remote={args.remote}:{args.port}")

    runner = GenericRemoteRunner(args.remote, args.port, tensor, args.output_dtype)
    start = time.perf_counter()
    outputs = runner.run(str(input_path))
    latency_ms = (time.perf_counter() - start) * 1000.0
    outputs = reshape_outputs(outputs, contract)

    source_image = _find_source_image(json_path, raw_json, args.source_image)
    annotated_output = None
    if not args.no_annotated and args.annotated_output:
        annotated_output = (output_path.parent / args.annotated_output).resolve()

    result = build_result(
        contract=contract,
        tensor=tensor,
        outputs=outputs,
        latency_ms=latency_ms,
        source_image=source_image,
        conf_thres=args.conf_thres,
        iou_thres=args.iou_thres,
        max_det=args.max_det,
        annotated_output=annotated_output,
    )
    save_json(result, output_path)
    print(f"[OK] wrote {output_path}")
    if "top1" in result:
        print(f"TOP1: {result['top1']}")
    if "detection_count" in result:
        print(f"DETECTIONS: {result['detection_count']}")
        for item in result.get("detections", [])[:5]:
            print(f"  {item['label']} {item['confidence']:.3f} {item['bbox_xyxy_original'] or item['bbox_xyxy_input']}")
        if result.get("annotated_image"):
            print(f"[OK] annotated image: {result['annotated_image']}")
    print(f"[INFO] latency_ms={latency_ms:.3f}")

    if args.update_json:
        raw_json["board_result"] = result
        save_json(raw_json, json_path)
        print(f"[OK] updated {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
