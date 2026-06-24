"""PC-side ONNX benchmark with optional real-image inference.

    edgeai benchmark -m model.onnx -r 50 -o outputs/benchmark/<name>.json
    edgeai benchmark -m model.onnx -r 50 -o out.json -i photo/cat.png

When --input is given the tool preprocesses the image, runs real inference,
and records classification / detection results alongside latency metrics.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort


# ================================================================
#  模型类型推断 & 图像预处理
# ================================================================

def _infer_model_type(model_path: Path) -> str:
    # Search both parent dir name and file stem
    parent = model_path.parent.name.lower().replace("-", "").replace("_", "")
    stem   = model_path.stem.lower().replace("-", "").replace("_", "")
    combined = f"{parent} {stem}"
    for keyword, mtype in [
        ("mnist", "mnist"), ("lenet", "mnist"),
        ("mobilenet", "mobilenetv2"),
        ("resnet", "resnet18"),
        ("yolo", "yolov5n"),
    ]:
        if keyword in combined:
            return mtype
    return parent  # fallback; caller may override via explicit model_type param


_PREPROCESS = {}  # populated below


def _register(model_type: str):
    def dec(fn):
        _PREPROCESS[model_type] = fn
        return fn
    return dec


@_register("mnist")
def _pre_mnist(image_path: Path, shape: list[int]) -> np.ndarray:
    from PIL import Image
    _, _, h, w = shape
    img = Image.open(image_path).convert("L").resize((w, h))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = (arr - 0.1307) / 0.3081
    return arr.reshape(1, 1, h, w).astype(np.float32)


@_register("mobilenetv2")
def _pre_mobilenet(image_path: Path, shape: list[int]) -> np.ndarray:
    from PIL import Image
    _, _, h, w = shape
    img = Image.open(image_path).convert("RGB").resize((w, h))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    # Force 3 channels: handle grayscale (2D), single-channel (H,W,1), or RGBA (H,W,4)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    elif arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)
    elif arr.shape[-1] == 4:
        arr = arr[:, :, :3]
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std
    return arr.transpose(2, 0, 1).reshape(1, 3, h, w).astype(np.float32)


@_register("resnet18")
def _pre_resnet(image_path: Path, shape: list[int]) -> np.ndarray:
    return _pre_mobilenet(image_path, shape)  # same ImageNet preprocessing


@_register("yolov5n")
def _pre_yolo(image_path: Path, shape: list[int]) -> np.ndarray:
    from PIL import Image
    _, _, h, w = shape
    img = Image.open(image_path).convert("RGB").resize((w, h))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    elif arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)
    elif arr.shape[-1] == 4:
        arr = arr[:, :, :3]
    return arr.transpose(2, 0, 1).reshape(1, 3, h, w).astype(np.float32)


def _generic_preprocess(image_path: Path, shape: list[int]) -> np.ndarray:
    """Fallback preprocessor for any 3-channel or 1-channel model."""
    from PIL import Image
    if len(shape) == 4:
        _, c, h, w = shape
    else:
        raise ValueError(f"Unsupported shape for generic preprocess: {shape}")
    if c in (1, 3):
        mode = "L" if c == 1 else "RGB"
        img = Image.open(image_path).convert(mode).resize((w, h))
        arr = np.asarray(img, dtype=np.float32) / 255.0
        if c == 3:
            if arr.ndim == 2:
                arr = np.stack([arr, arr, arr], axis=-1)
            elif arr.shape[-1] == 1:
                arr = np.repeat(arr, 3, axis=-1)
            elif arr.shape[-1] == 4:
                arr = arr[:, :, :3]
            arr = arr.transpose(2, 0, 1)
        return arr.reshape(1, c, h, w).astype(np.float32)
    raise ValueError(f"Unsupported channels={c} for generic preprocess")


# ================================================================
#  输出解码
# ================================================================

def _softmax_topk(values: np.ndarray, k: int = 5) -> list[dict]:
    shifted = values - values.max()
    probs = np.exp(shifted) / np.exp(shifted).sum()
    top_idx = probs.argsort()[-1:-(k + 1):-1]
    return [{"index": int(i), "prob": float(probs[i])} for i in top_idx]


def _decode_classification(outputs: list[np.ndarray]) -> dict:
    if not outputs:
        return {}
    top5 = _softmax_topk(outputs[0].flatten())
    return {
        "predict": top5[0]["index"],
        "top5": top5,
    }


# ----------------------------------------------------------------
#  YOLO decoder (minimal, kept here to avoid adding a heavy dep)
# ----------------------------------------------------------------

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


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x.astype(np.float32), -80, 80)))


def _xywh2xyxy(b: np.ndarray) -> np.ndarray:
    out = np.empty_like(b)
    out[:, 0] = b[:, 0] - b[:, 2] / 2
    out[:, 1] = b[:, 1] - b[:, 3] / 2
    out[:, 2] = b[:, 0] + b[:, 2] / 2
    out[:, 3] = b[:, 1] + b[:, 3] / 2
    return out


def _nms(boxes, scores, class_ids, iou_thres, max_det=20):
    keep = []
    for cid in np.unique(class_ids):
        idx = np.where(class_ids == cid)[0]
        order = idx[np.argsort(scores[idx])[::-1]]
        while order.size and len(keep) < max_det:
            cur = int(order[0])
            keep.append(cur)
            if order.size == 1:
                break
            ious = _box_iou(boxes[cur], boxes[order[1:]])
            order = order[1:][ious <= iou_thres]
    keep.sort(key=lambda i: float(scores[i]), reverse=True)
    return keep[:max_det]


def _box_iou(box, boxes):
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    a1 = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
    a2 = np.maximum(0.0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0.0, boxes[:, 3] - boxes[:, 1])
    return inter / np.maximum(a1 + a2 - inter, 1e-6)


def _draw_detections(image_path: Path, detections: list[dict], output_path: Path) -> str:
    from PIL import Image, ImageDraw
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    for item in detections:
        box = item["bbox_xyxy_original"] or item["bbox_xyxy_input"]
        if not box:
            continue
        cid = int(item["class_id"])
        color = ((37 * cid + 23) % 255, (17 * cid + 113) % 255, (29 * cid + 71) % 255)
        label = f"{item['label']} {item['confidence']:.2f}"
        draw.rectangle(box, outline=color, width=3)
        left, top = box[0], max(0, box[1] - 14)
        draw.rectangle([left, top, left + max(60, 7 * len(label)), top + 14], fill=color)
        draw.text((left + 2, top + 1), label, fill=(255, 255, 255))
    img.save(output_path)
    return str(output_path)


def _decode_yolo(outputs: list[np.ndarray], model_shape: list[int],
                 image_path: Optional[Path], output_dir: Path,
                 conf=0.25, iou=0.45) -> dict:
    if not outputs or image_path is None:
        return {}
    pred = outputs[0].astype(np.float32)
    if pred.ndim == 3:
        pred = pred[0]
    if pred.ndim == 2 and pred.shape[0] == 85 and pred.shape[1] != 85:
        pred = pred.T
    if pred.ndim != 2 or pred.shape[1] < 6:
        return {"detection_count": 0, "detections": []}

    _, _, input_h, input_w = model_shape
    boxes = _xywh2xyxy(pred[:, :4])
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, input_w)
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, input_h)

    obj = _sigmoid(pred[:, 4]) if pred[:, 4].min() < 0 or pred[:, 4].max() > 1 else pred[:, 4]
    cls = pred[:, 5:]
    cls = _sigmoid(cls) if cls.min() < 0 or cls.max() > 1 else cls
    class_ids = cls.argmax(axis=1)
    class_conf = cls[np.arange(cls.shape[0]), class_ids]
    scores = obj * class_conf
    valid = scores >= conf

    if not np.any(valid):
        return {"detection_count": 0, "detections": []}

    boxes = boxes[valid]; scores = scores[valid]
    class_ids = class_ids[valid]

    # scale boxes to original image size (assume square resize for now)
    from PIL import Image
    with Image.open(image_path) as im:
        orig_w, orig_h = im.size
    sx, sy = orig_w / input_w, orig_h / input_h

    keep = _nms(boxes, scores, class_ids, iou, 20)
    detections = []
    for idx in keep:
        cid = int(class_ids[idx])
        box = boxes[idx]
        detections.append({
            "class_id": cid,
            "label": COCO_CLASSES[cid] if cid < len(COCO_CLASSES) else f"class_{cid}",
            "confidence": float(scores[idx]),
            "bbox_xyxy_input": [float(x) for x in box],
            "bbox_xyxy_original": [
                int(round(box[0] * sx)), int(round(box[1] * sy)),
                int(round(box[2] * sx)), int(round(box[3] * sy)),
            ],
        })

    annotated_path = output_dir / f"{Path(image_path).stem}_yolo.jpg"
    annotated = _draw_detections(image_path, detections, annotated_path)

    return {"detection_count": len(detections), "detections": detections,
            "annotated_image": annotated}


# ================================================================
#  主入口
# ================================================================

def benchmark_model(
    model,          # Path or str
    repeat: int,
    output,         # Path or str
    input_image=None,  # optional Path/str
    model_type=None,   # optional explicit override e.g. "mobilenetv2"
):
    """Run ONNX benchmark.

    Args:
        model:       ONNX model path.
        repeat:      number of inference runs (after 10 warmup).
        output:      output JSON path.
        input_image: optional real image. If None, use random dummy data.
        model_type:  optional explicit type (mnist/mobilenetv2/resnet18/yolov5n).
                     If None, inferred from model path.
    """
    model = Path(model)
    output = Path(output)

    sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]

    # --- resolve shape ---
    shape = []
    for dim in inp.shape:
        shape.append(dim if isinstance(dim, int) and dim > 0 else 1)
    print(f"Benchmarking: {model.name}")
    print(f"  Input name : {inp.name}")
    print(f"  Shape      : {shape}")

    # --- determine tensor ---
    model_type = model_type or _infer_model_type(model)
    real_input = input_image is not None
    if real_input:
        img_path = Path(input_image).expanduser().resolve()
        if not img_path.exists():
            raise FileNotFoundError(f"input image not found: {img_path}")
        print(f"  Input image: {img_path}")
        preprocess = _PREPROCESS.get(model_type)
        if preprocess is None:
            print(f"  [INFO] no specific preprocessor for '{model_type}', using generic")
            preprocess = _generic_preprocess
        tensor = preprocess(img_path, shape)
        print(f"  Tensor shape: {list(tensor.shape)}  dtype: {tensor.dtype}")
        # Fixup common mismatches: grayscale replicated to 3-channel, etc.
        if list(tensor.shape) != shape:
            if tensor.ndim == 4 and tensor.shape[1] == 1 and shape[1] == 3:
                tensor = np.repeat(tensor, 3, axis=1)
                print(f"  [FIXED] replicated channel → {list(tensor.shape)}")
            if list(tensor.shape) != shape:
                raise ValueError(
                    f"Cannot fix shape: got {list(tensor.shape)}, "
                    f"model expects {shape}"
                )
    else:
        tensor = np.random.rand(*shape).astype(np.float32)

    # --- warmup ---
    for _ in range(10):
        sess.run(None, {inp.name: tensor})

    # --- timed runs ---
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        sess.run(None, {inp.name: tensor})
        times.append((time.perf_counter() - t0) * 1000)

    # --- real inference output (only when image is provided) ---
    if real_input:
        outputs = sess.run(None, {inp.name: tensor})

        # classification
        cls_result = _decode_classification(outputs)

        # detection (only for YOLO)
        yolo_result = {}
        if model_type == "yolov5n":
            output_dir = output.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            yolo_result = _decode_yolo(outputs, shape, img_path, output_dir)
    else:
        cls_result, yolo_result = {}, {}

    # --- build result ---
    result = {
        "model": model.parent.name,
        "model_type": model_type,
        "repeat": repeat,
        "model_size_mb": round(model.stat().st_size / (1024 * 1024), 3),
        "input_file": str(input_image) if real_input else "dummy_random",
        "input_type": "image" if real_input else "dummy",
        "avg_latency_ms": round(float(np.mean(times)), 3),
        "p50_ms": round(float(np.percentile(times, 50)), 3),
        "p95_ms": round(float(np.percentile(times, 95)), 3),
        "min_ms": round(float(np.min(times)), 3),
        "max_ms": round(float(np.max(times)), 3),
    }

    if cls_result:
        result.update(cls_result)
    if yolo_result:
        result.update(yolo_result)

    # --- save ---
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nSaved -> {output}")
