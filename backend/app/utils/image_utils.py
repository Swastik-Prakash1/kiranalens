# backend/app/utils/image_utils.py
"""
KiranaLens v4.0 — Detection Visualization Utilities.

Draws color-coded bounding boxes on shelf images using category intelligence.
Returns base64-encoded JPEG strings for frontend display.
"""

import base64
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# BGR color palette for each retail category
CATEGORY_COLORS_BGR: dict[str, tuple[int, int, int]] = {
    "Packaged Foods":     (0, 200, 100),    # green
    "Beverages":          (200, 100, 0),     # blue
    "Dairy Products":     (255, 200, 0),     # cyan
    "Personal Care":      (0, 100, 255),     # orange
    "Household Items":    (180, 0, 180),     # purple
    "Snacks":             (0, 200, 255),     # yellow
    "Staples":            (150, 150, 0),     # olive
    "Cooking Oils":       (50, 180, 220),    # gold
    "Mobile Accessories": (255, 80, 80),     # light blue
    "Electronics":        (255, 50, 50),     # blue
    "Stationery":         (100, 200, 200),   # beige
    "Health & Wellness":  (100, 255, 100),   # light green
    "Chocolates":         (30, 80, 160),     # brown
    "Cleaning":           (200, 200, 0),     # teal
    "Other Items":        (120, 120, 120),   # gray
}
DEFAULT_COLOR: tuple[int, int, int] = (80, 200, 80)


def draw_category_annotations(
    img_bgr: np.ndarray,
    coco_boxes: list,
    coco_class_names: dict[int, str],
    foduucom_boxes: list,
    img_height: int,
) -> str:
    """
    Draw annotated bounding boxes on the image.
    Returns base64 encoded JPEG string for frontend display.
    """
    from app.services.category_intelligence import (
        COCO_TO_RETAIL_CATEGORY, ZONE_CATEGORY_MAP, classify_zone,
    )

    annotated = img_bgr.copy()

    # Draw COCO detections with category labels
    for box in (coco_boxes or []):
        try:
            bbox = box.xyxy[0].tolist()
            cls_id = int(box.cls[0].item())
            class_name = coco_class_names.get(cls_id, "unknown")
            category = COCO_TO_RETAIL_CATEGORY.get(class_name, "Other Items")
            color = CATEGORY_COLORS_BGR.get(category, DEFAULT_COLOR)

            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Label background
            label = category
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
            cv2.putText(
                annotated, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA,
            )
        except Exception:
            continue

    # Draw foduucom detections (lighter, zone-based label)
    for box in (foduucom_boxes or []):
        try:
            bbox = box.xyxy[0].tolist()
            y_c = (bbox[1] + bbox[3]) / 2
            zone = classify_zone(y_c, img_height)
            cats = ZONE_CATEGORY_MAP.get(zone, ["Other Items"])
            color = CATEGORY_COLORS_BGR.get(cats[0], DEFAULT_COLOR)
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)
        except Exception:
            continue

    # Encode to base64
    _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    b64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"
