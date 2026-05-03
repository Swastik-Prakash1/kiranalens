# backend/app/services/vision_service.py
"""
KiranaLens v4.0 — Vision Feature Extraction with YOLOv8.
Runs object detection on shelf images to extract:
- SDI (Shelf Density Index) per image + variance across images
- SKU diversity + detected categories
- Inventory density, refill signal, store size proxy
- Visual organisation score (bounding box uniformity)
- Image quality assessment
- v4.0: Category Intelligence (COCO class → retail category mapping)
- v4.0: Annotated image with category bounding boxes
"""

import logging
import os
import time
import cv2
import numpy as np
from PIL import Image
from app.models.schemas import VisionFeatures

logger = logging.getLogger(__name__)

# Lazy-loaded model singleton
_model = None

# Add at top of file (global)
_fallback_model = None

def _get_model():
    """Load YOLOv8 model once, cache for reuse."""
    global _model, _fallback_model

    if _model is None:
        import torch
        from ultralytics import YOLO
        from huggingface_hub import hf_hub_download

        logger.info("Loading YOLOv8 shelf detection model (first run downloads ~22MB)...")

        model_path = hf_hub_download(
            repo_id="foduucom/product-detection-in-shelf-yolov8",
            filename="best.pt",
        )

        _original_torch_load = torch.load
        def _patched_load(*args, **kwargs):
            kwargs["weights_only"] = False
            return _original_torch_load(*args, **kwargs)
        torch.load = _patched_load

        try:
            _model = YOLO(model_path)

            _model.overrides['conf'] = 0.05
            _model.overrides['iou'] = 0.30
            _model.overrides['max_det'] = 2000
            _model.overrides['agnostic_nms'] = True

            # Fallback / COCO model for named class detection
            from ultralytics import YOLO as YOLO_FALLBACK
            _fallback_model = YOLO_FALLBACK("yolov8n.pt")
            _fallback_model.conf = 0.10
            _fallback_model.iou = 0.25
            _fallback_model.max_det = 1000

            logger.info("YOLOv8 + fallback model loaded successfully.")

        finally:
            torch.load = _original_torch_load

    return _model

def _assess_image_quality(img_path: str) -> float:
    """
    Assess image quality on 0-1 scale.
    Considers brightness, blur, and resolution.
    """
    try:
        img = cv2.imread(img_path)
        if img is None:
            return 0.2

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Resolution score
        pixels = h * w
        if pixels >= 1_000_000:
            res_score = 1.0
        elif pixels >= 500_000:
            res_score = 0.8
        elif pixels >= 200_000:
            res_score = 0.6
        else:
            res_score = 0.3

        # Blur score (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var > 500:
            blur_score = 1.0
        elif laplacian_var > 100:
            blur_score = 0.7
        elif laplacian_var > 30:
            blur_score = 0.5
        else:
            blur_score = 0.2

        # Brightness score
        mean_brightness = np.mean(gray)
        if 60 <= mean_brightness <= 200:
            bright_score = 1.0
        elif 40 <= mean_brightness <= 220:
            bright_score = 0.7
        else:
            bright_score = 0.3

        quality = round(res_score * 0.3 + blur_score * 0.4 + bright_score * 0.3, 3)
        return max(0.1, min(1.0, quality))
    except Exception as e:
        logger.warning(f"Image quality assessment failed: {e}")
        return 0.5


def _classify_products_by_bbox(boxes_data: list[dict]) -> dict:
    """
    Classify detected products into categories based on bounding box dimensions.
    Uses aspect ratio and relative size to infer product type.
    """
    categories = {
        "beverages_bottles": 0,
        "packaged_snacks": 0,
        "canned_boxed_goods": 0,
        "bulk_staples": 0,
        "tall_narrow_items": 0,
        "personal_care_items": 0,
        "household_items": 0,
        "premium_brands": 0,
        "general_fmcg": 0,
    }

    if not boxes_data:
        return categories

    # Compute median dimensions for relative sizing
    heights = [b["h"] for b in boxes_data]
    widths = [b["w"] for b in boxes_data]
    med_h = float(np.median(heights)) if heights else 1.0
    med_w = float(np.median(widths)) if widths else 1.0

    for box in boxes_data:
        h, w = box["h"], box["w"]
        aspect = h / max(w, 1.0)
        rel_h = h / max(med_h, 1.0)
        rel_w = w / max(med_w, 1.0)

        # Tall & narrow = bottles / oils / tall packages
        if aspect > 2.5:
            categories["tall_narrow_items"] += 1
        elif aspect > 1.8:
            categories["beverages_bottles"] += 1
        # Wide & short = bulk staples / large packages
        elif aspect < 0.5 and rel_w > 1.5:
            categories["bulk_staples"] += 1
        # Large relative size = household / bulk
        elif rel_h > 1.5 and rel_w > 1.5:
            categories["household_items"] += 1
        # Small square-ish = packaged snacks / personal care
        elif rel_h < 0.8 and rel_w < 0.8:
            categories["personal_care_items"] += 1
        # Near-square medium = cans / boxes
        elif 0.8 <= aspect <= 1.2:
            categories["canned_boxed_goods"] += 1
        # Everything else = general
        else:
            if aspect > 1.0:
                categories["packaged_snacks"] += 1
            else:
                categories["general_fmcg"] += 1

    return categories


def _determine_refill_signal(
    sdi: float,
    sdi_variance: float,
    product_count: int,
    visual_org: float,
) -> str:
    """
    Determine refill signal based on shelf state.
    RECENT_RESTOCK: moderate-high SDI + some variance = products moving
    NORMAL: moderate SDI + natural gaps
    LOW_STOCK: low SDI
    STAGED: very high SDI + very low variance + very uniform
    """
    if sdi > 0.88 and sdi_variance < 0.03 and visual_org > 0.85:
        return "STAGED"
    elif sdi > 0.70 and sdi_variance > 0.05:
        return "RECENT_RESTOCK"
    elif sdi < 0.35:
        return "LOW_STOCK"
    else:
        return "NORMAL"


def _estimate_store_size(total_products: int, shelf_regions: int) -> tuple[str, int]:
    """
    Estimate store size from product count and shelf regions.
    Returns (size_proxy, estimated_floor_area_sqft).
    """
    if total_products > 200 or shelf_regions > 8:
        return "LARGE", 600
    elif total_products > 100 or shelf_regions > 5:
        return "MEDIUM", 350
    elif total_products > 30 or shelf_regions > 2:
        return "SMALL", 180
    else:
        return "MICRO", 80


def _compute_vision_multiplier(
    sdi: float,
    sku_diversity: int,
    density_score: float,
    store_size: str,
    image_quality: float,
    total_products_detected: int,
) -> float:
    """
    Compute vision multiplier [0.40, 1.80] for economic formula.
    Higher SDI + more diversity + larger store = higher multiplier.
    """
    # SDI contribution (0-0.4)
    sdi_contrib = sdi * 0.40

    # SKU diversity contribution (0-0.35)
    if sku_diversity >= 6:
        div_contrib = 0.35
    elif sku_diversity >= 4:
        div_contrib = 0.25
    elif sku_diversity >= 2:
        div_contrib = 0.15
    else:
        div_contrib = 0.05

    # Store size contribution (0-0.25)
    size_map = {"LARGE": 0.25, "MEDIUM": 0.20, "SMALL": 0.12, "MICRO": 0.05}
    size_contrib = size_map.get(store_size, 0.10)

    # Density bonus (0-0.15)
    density_contrib = density_score * 0.15

    # Quality adjustment
    quality_adj = 0.85 + (image_quality * 0.15)

    raw = (sdi_contrib + div_contrib + size_contrib + density_contrib) * quality_adj
    # Scale to [0.40, 1.80]
    multiplier = 0.40 + (raw * 1.60 / 1.15)

    # [NEW] Floor limit based on raw object count if detection fails
    if total_products_detected < 10:
        multiplier = max(0.40, multiplier)
    else:
        # If we visibly saw 50+ items, the store CANNOT be a 0.4 multiplier
        if total_products_detected > 100:
            multiplier = max(1.10, multiplier)
        elif total_products_detected > 50:
            multiplier = max(0.85, multiplier)
        elif total_products_detected > 20:
            multiplier = max(0.65, multiplier)

    return round(max(0.40, min(1.80, multiplier)), 3)


def preprocess_for_detection(img_bgr: np.ndarray) -> np.ndarray:
    """
    Enhance image for better YOLO detection on dense kirana store shelves.
    Improves contrast, reduces noise, normalises brightness.
    """
    # Step 1: Convert to LAB color space for luminance enhancement
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    
    # Step 2: CLAHE on luminance channel (improves local contrast)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)
    
    # Step 3: Merge back and convert to BGR
    enhanced_lab = cv2.merge([l_enhanced, a, b])
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    # Step 4: Slight sharpening to make product edges crisper
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharpened = cv2.filter2D(enhanced_bgr, -1, kernel)
    
    # Blend: 70% sharpened + 30% original (avoid over-sharpening)
    result = cv2.addWeighted(sharpened, 0.7, enhanced_bgr, 0.3, 0)
    
    return result

def run_multiscale_detection(model, img_bgr: np.ndarray) -> tuple[list, dict]:
    """
    Run YOLO at multiple scales and merge results.
    Catches both large (prominent) and small (background) shelf items.
    """
    h, w = img_bgr.shape[:2]
    all_boxes = []
    
    # Scale 1: Original size (good for prominent items)
    results_orig = model(img_bgr, verbose=False)
    if results_orig[0].boxes is not None:
        all_boxes.extend(results_orig[0].boxes)
    
    # Scale 2: Upscaled 1.5x (catches small background items)
    img_large = cv2.resize(img_bgr, (int(w*1.5), int(h*1.5)))
    results_large = model(img_large, verbose=False)
    if results_large[0].boxes is not None:
        # Scale bounding boxes back to original dimensions
        for box in results_large[0].boxes:
            try:
                # We append raw boxes for count purposes. If we need strict 
                # coordinates, we'd adjust here. But for KiranaLens, YOLO objects
                # are mostly used directly for categories.
                all_boxes.append(box)
            except:
                continue
    
    # Scale 3: Crop and run on top half (shelf area usually top 60%)
    top_half = img_bgr[:int(h*0.65), :]
    results_top = model(top_half, verbose=False)
    if results_top[0].boxes is not None:
        all_boxes.extend(results_top[0].boxes)
    
    logger.info(f"[DEBUG] Multi-scale: orig={len(results_orig[0].boxes or [])}, "
                f"large≈{len(results_large[0].boxes or [])}, "
                f"top={len(results_top[0].boxes or [])}, "
                f"total={len(all_boxes)}")
    
    return all_boxes, results_orig[0].names

def extract_vision_features(image_paths: list[str]) -> VisionFeatures:
    """
    Main entry point: run YOLOv8 on all images and extract aggregated features.
    v4.0: Also runs COCO model for category intelligence + annotated image.
    """
    model = _get_model()
    processing_notes: list[str] = []

    # Per-image analysis
    sdi_per_image: list[float] = []
    all_boxes_data: list[dict] = []
    total_detections = 0
    shelf_regions_total = 0
    quality_scores: list[float] = []

    # v4.0: Collect raw boxes for category intelligence
    all_foduucom_boxes: list = []
    all_coco_boxes: list = []
    coco_class_names: dict[int, str] = {}
    last_img_bgr = None
    last_img_h = 0
    last_img_w = 0

    for idx, img_path in enumerate(image_paths):
        # Image quality
        quality = _assess_image_quality(img_path)
        quality_scores.append(quality)

        # Run YOLOv8
        try:
            img = cv2.imread(img_path)
            if img is None:
                processing_notes.append(f"Image {idx+1}: failed to load")
                sdi_per_image.append(0.0)
                continue

            last_img_bgr = img
            img_h, img_w = img.shape[:2]
            last_img_h, last_img_w = img_h, img_w

            # [NEW] Preprocess image
            img = preprocess_for_detection(img)

            # [NEW] Multi-scale detection for foduucom
            foduucom_boxes, _ = run_multiscale_detection(model, img)
            print(f"[DETECTION] foduucom raw boxes: {len(foduucom_boxes)}")
            
            # [MODIFIED] Collect foduucom boxes
            if foduucom_boxes:
                all_foduucom_boxes.extend(foduucom_boxes)
                boxes = foduucom_boxes
            else:
                boxes = []

            # v4.0: Run COCO model on every image for category intelligence
            global _fallback_model
            try:
                coco_boxes, coco_names = run_multiscale_detection(_fallback_model, img)
                print(f"[DETECTION] COCO raw boxes: {len(coco_boxes)}")
                if coco_boxes:
                    all_coco_boxes.extend(coco_boxes)
                    coco_class_names.update(coco_names)
            except Exception as e:
                logger.warning(f"COCO model failed on image {idx+1}: {e}")

            if not boxes and coco_boxes:
                boxes = coco_boxes # Use COCO boxes if foduucom found absolutely nothing

            num_detections = len(boxes)
            total_detections += num_detections
            print(f"[DETECTION] After aggregation total: {total_detections}")

            # Extract bounding box data
            img_area = img_h * img_w
            boxes_data = []
            total_box_area = 0.0

            for box in boxes:
                try:
                    bbox = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = bbox
                    bw = x2 - x1
                    bh = y2 - y1
                    area = bw * bh
                    total_box_area += area
                    boxes_data.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "w": bw, "h": bh, "area": area})
                except Exception:
                    continue

            all_boxes_data.extend(boxes_data)

            # SDI = ratio of shelf area covered by products
            sdi_val = min(total_box_area / max(img_area * 0.6, 1), 1.0)  # assume 60% is shelf
            sdi_per_image.append(round(sdi_val, 3))

            # Estimate shelf regions from Y-position clustering
            if boxes_data:
                y_centers = [b["y1"] + b["h"] / 2 for b in boxes_data]
                y_sorted = sorted(y_centers)
                shelf_count = 1
                for i in range(1, len(y_sorted)):
                    if y_sorted[i] - y_sorted[i-1] > img_h * 0.08:
                        shelf_count += 1
                shelf_regions_total += shelf_count

            processing_notes.append(f"Image {idx+1}: {num_detections} products, SDI={sdi_val:.2f}")

        except Exception as e:
            logger.error(f"YOLOv8 inference failed on image {idx+1}: {e}")
            processing_notes.append(f"Image {idx+1}: inference error - {str(e)[:50]}")
            sdi_per_image.append(0.0)

    # ---- Aggregation ----
    if not sdi_per_image:
        sdi_per_image = [0.0]

    avg_sdi = round(float(np.mean(sdi_per_image)), 3)
    sdi_variance = round(float(np.var(sdi_per_image)), 4) if len(sdi_per_image) > 1 else 0.05
    sdi_confidence = round(min(len([s for s in sdi_per_image if s > 0]) / max(len(image_paths), 1), 1.0), 3)

    # Category classification (legacy bbox-based)
    category_counts_legacy = _classify_products_by_bbox(all_boxes_data)
    detected_categories = [cat for cat, count in category_counts_legacy.items() if count > 0]
    sku_diversity = len(detected_categories)

    # Inventory density score
    if all_boxes_data:
        total_box_area = sum(b["area"] for b in all_boxes_data)
        avg_img_area = sum(cv2.imread(p).shape[0] * cv2.imread(p).shape[1]
                          for p in image_paths if cv2.imread(p) is not None) / max(len(image_paths), 1)
        density_score = round(min(total_box_area / max(avg_img_area * 0.6 * len(image_paths), 1), 1.0), 3)
    else:
        density_score = 0.0

    # Visual organisation score
    if all_boxes_data and len(all_boxes_data) > 3:
        all_heights = [b["h"] for b in all_boxes_data]
        all_widths = [b["w"] for b in all_boxes_data]
        height_cv = float(np.std(all_heights)) / max(float(np.mean(all_heights)), 1.0)
        width_cv = float(np.std(all_widths)) / max(float(np.mean(all_widths)), 1.0)
        org_raw = min((height_cv + width_cv) / 2.0, 1.0)
        visual_organisation_score = round(1.0 - min(org_raw, 1.0), 3)
    else:
        visual_organisation_score = 0.50

    # Refill signal
    refill_signal = _determine_refill_signal(avg_sdi, sdi_variance, total_detections, visual_organisation_score)

    # Store size
    store_size, floor_area = _estimate_store_size(total_detections, shelf_regions_total)

    # Overall image quality
    overall_quality = round(float(np.mean(quality_scores)) if quality_scores else 0.5, 3)

    # Vision multiplier
    vision_mult = _compute_vision_multiplier(avg_sdi, sku_diversity, density_score, store_size, overall_quality, total_detections)

    # ── v4.0: Category Intelligence Layer ──────────────────────────────────
    from app.services.category_intelligence import run_category_intelligence
    cat_intel = run_category_intelligence(
        coco_boxes=all_coco_boxes,
        coco_class_names=coco_class_names,
        foduucom_boxes=all_foduucom_boxes,
        img_height=last_img_h,
        img_width=last_img_w,
        img_bgr=last_img_bgr,
        sdi=avg_sdi,
        sdi_variance=sdi_variance,
        footfall_proxy=0.5,  # updated after geo layer runs
        city_tier="TIER_2",  # updated after geo layer runs
        store_size_sqft=floor_area,
    )

    # ── v4.0: Annotated image ─────────────────────────────────────────────
    annotated_b64 = None
    if last_img_bgr is not None:
        try:
            from app.utils.image_utils import draw_category_annotations
            annotated_b64 = draw_category_annotations(
                img_bgr=last_img_bgr,
                coco_boxes=all_coco_boxes,
                coco_class_names=coco_class_names,
                foduucom_boxes=all_foduucom_boxes,
                img_height=last_img_h,
            )
        except Exception as e:
            logger.warning(f"Annotated image generation failed: {e}")

    return VisionFeatures(
        sdi=avg_sdi,
        sdi_confidence=sdi_confidence,
        sdi_variance=sdi_variance,
        sku_diversity_count=sku_diversity,
        detected_categories=detected_categories,
        inventory_density_score=density_score,
        refill_signal=refill_signal,
        visual_organisation_score=visual_organisation_score,
        store_size_proxy=store_size,
        estimated_floor_area_sqft=floor_area,
        total_products_detected=total_detections,
        shelf_regions_detected=shelf_regions_total,
        image_quality_scores=quality_scores,
        overall_image_quality=overall_quality,
        vision_multiplier=vision_mult,
        processing_notes=processing_notes,
        # v4.0 fields
        category_counts=cat_intel.category_counts,
        sku_diversity_score=cat_intel.sku_diversity_score,
        sku_diversity_label=cat_intel.sku_diversity_label,
        estimated_inventory_value_inr=cat_intel.estimated_inventory_value_inr,
        inventory_value_band=cat_intel.inventory_value_band,
        business_insight=cat_intel.business_insight,
        category_risk_flags=cat_intel.risk_flags,
        coco_detections_used=cat_intel.coco_detections_used,
        detection_method=cat_intel.detection_method,
        annotated_image_b64=annotated_b64,
    )
