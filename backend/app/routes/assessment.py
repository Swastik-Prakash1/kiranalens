# backend/app/routes/assessment.py
"""
KiranaLens v4.0 — API Routes.
Endpoints: /health, /demo, /assess
"""

import logging
import os
import time
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from app.models.schemas import (
    AssessmentResponse, VisionFeatures, GeoFeatures,
    OperationalStabilityResult, RegionalDemandResult,
    EconomicEstimate, FraudAnalysis, RiskFlag, LoanRecommendation,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint -- verifies all services."""
    checks = {
        "status": "healthy",
        "version": "4.0.0",
        "model": "KL-v4.0",
        "services": {}
    }

    # Check YOLOv8
    try:
        from app.services.vision_service import _get_model
        _get_model()
        checks["services"]["yolov8"] = "ready"
    except Exception as e:
        checks["services"]["yolov8"] = f"error: {str(e)[:50]}"

    # Check HF token
    hf_token = os.getenv("HF_TOKEN", "")
    if hf_token and "your_token" not in hf_token:
        checks["services"]["hf_api"] = "configured"
    else:
        checks["services"]["hf_api"] = "not_configured (demo mode only)"

    # Check geo
    checks["services"]["osm_geo"] = "ready"

    # Check stability + regional + category intelligence
    checks["services"]["stability_signal"] = "ready"
    checks["services"]["regional_demand"] = "ready"
    checks["services"]["category_intelligence"] = "ready"

    return checks

@router.get("/debug/category-test")
async def debug_category_test():
    """Quick test of category intelligence with simulated zero-detection scenario."""
    from app.services.category_intelligence import run_category_intelligence
    
    result = run_category_intelligence(
        coco_boxes=[],
        coco_class_names={},
        foduucom_boxes=[],
        img_height=640,
        img_width=480,
        sdi=0.11,
        sdi_variance=0.05,
        footfall_proxy=0.34,
        city_tier="TIER_3",
    )
    
    return {
        "category_counts": result.category_counts,
        "total_categories": result.total_unique_categories,
        "inventory_value": result.estimated_inventory_value_inr,
        "inventory_band": result.inventory_value_band,
        "sku_diversity_score": result.sku_diversity_score,
        "sku_diversity_label": result.sku_diversity_label,
        "detection_method": getattr(result, "detection_method", "unknown"),
    }


@router.get("/debug/heuristic-variance")
async def debug_heuristic_variance():
    import numpy as np
    from app.services.category_intelligence import compute_image_responsive_heuristic

    # Simulate two different images using different pixel values
    img1 = np.ones((640,480,3), dtype=np.uint8) * 180   # bright store
    img1[100:200, :] = [50, 100, 200]   # blue zone (beverages)
    img1[300:400, :] = [200, 50, 50]    # red zone (packaged foods)

    img2 = np.ones((640,480,3), dtype=np.uint8) * 100   # darker store
    img2[100:200, :] = [50, 200, 50]    # green zone (vegetables/staples)
    img2[400:500, :] = [200, 200, 50]   # yellow zone (packaged)

    counts1 = compute_image_responsive_heuristic(img1, 0, 0.75)
    counts2 = compute_image_responsive_heuristic(img2, 0, 0.30)

    return {
        "bright_store_SDI_0.75": counts1,
        "dark_store_SDI_0.30": counts2,
        "are_different": counts1 != counts2,
    }


@router.get("/demo")
async def demo_assessment():
    """
    Demo endpoint -- returns a complete hardcoded v4.0 assessment.
    Works with ZERO setup. Judges see impressive results instantly.
    No HF token, no images needed.
    """
    return AssessmentResponse(
        assessment_id=f"KL-{datetime.now().strftime('%Y%m%d-%H%M%S')}-DEMO",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        status="COMPLETE",
        inputs={
            "shop_name": "Rahatani Kirana & General Store",
            "lat": 18.62,
            "lng": 73.74,
            "images_count": 3,
            "years_in_operation": 5,
            "mode": "demo"
        },
        vision_features=VisionFeatures(
            sdi=0.78,
            sdi_confidence=0.82,
            sdi_variance=0.042,
            sku_diversity_count=7,
            detected_categories=["beverages_bottles", "packaged_snacks", "canned_boxed_goods",
                                  "bulk_staples", "tall_narrow_items", "personal_care_items",
                                  "general_fmcg"],
            inventory_density_score=0.72,
            refill_signal="NORMAL",
            visual_organisation_score=0.68,
            store_size_proxy="SMALL",
            estimated_floor_area_sqft=180,
            total_products_detected=252,
            shelf_regions_detected=6,
            image_quality_scores=[0.84, 0.81, 0.87],
            overall_image_quality=0.84,
            vision_multiplier=1.10,
            processing_notes=[
                "Image 1: 92 products, SDI=0.80",
                "Image 2: 85 products, SDI=0.76",
                "Image 3: 75 products, SDI=0.78",
            ],
            # v4.0 Category Intelligence
            category_counts={
                "Packaged Foods": 128,
                "Beverages": 42,
                "Personal Care": 26,
                "Dairy Products": 18,
                "Household Items": 15,
                "Other Items": 23,
            },
            sku_diversity_score=0.72,
            sku_diversity_label="High",
            estimated_inventory_value_inr=68500,
            inventory_value_band="Medium",
            business_insight=(
                "Good shelf utilisation with diverse SKU mix across 6 categories "
                "in a high-footfall area, indicating stable demand and healthy turnover. "
                "Primary stock: Packaged Foods."
            ),
            category_risk_flags=[],
            coco_detections_used=87,
            detection_method="coco+spatial",
            annotated_image_b64=None,
        ),
        geo_features=GeoFeatures(
            lat=18.62,
            lng=73.74,
            city_tier="TIER_2",
            india_region="west_india",
            road_type="RESIDENTIAL",
            road_type_score=0.40,
            nearby_amenities={
                "shops": 8, "restaurants": 3, "banks_atms": 2,
                "schools": 1, "hospitals": 1, "transit_stops": 2,
                "places_of_worship": 1, "fuel_stations": 1,
            },
            amenity_score=0.72,
            competition_count_300m=3,
            competition_count_500m=5,
            competition_density_score=0.55,
            competition_adjustment=1.10,
            catchment_density_score=0.68,
            footfall_proxy_index=0.72,
            geo_multiplier=1.08,
            data_confidence=0.80,
            fallback_used=False,
        ),
        operational_stability=OperationalStabilityResult(
            stability_score=0.76,
            stability_factor=1.05,
            stability_grade="HIGH",
            possible_initial_stocking=False,
            stability_explanation=(
                "Natural shelf gaps indicate products are actively selling. "
                "Inventory levels are consistent across all submitted images. "
                "Store reports 5 years of operation -- strong maturity signal. "
                "Overall stability grade: HIGH (score: 0.76). Formula factor: 1.05x."
            ),
            signals_used={
                "sdi_level_score": 0.82,
                "consistency_score": 0.88,
                "refill_score": 1.00,
                "organisation_score": 0.85,
                "years_bonus": 0.12,
                "years_provided": True,
            },
        ),
        regional_demand=RegionalDemandResult(
            india_region="west_india",
            regional_alignment_score=0.74,
            demand_alignment_factor=1.02,
            alignment_grade="STRONG",
            expected_categories=sorted([
                "snacks_namkeen", "beverages_cold", "packaged_food", "biscuits",
                "edible_oils_groundnut", "beverages_tea", "dairy_products",
                "personal_care", "household_care", "packaged_spices",
                "instant_noodles", "atta_wheat_flour",
            ]),
            detected_matching=sorted([
                "beverages_cold", "beverages_tea", "biscuits",
                "packaged_food", "personal_care", "snacks_namkeen",
            ]),
            detected_missing=sorted([
                "atta_wheat_flour", "dairy_products",
                "edible_oils_groundnut", "household_care",
                "instant_noodles", "packaged_spices",
            ]),
            demand_mismatch=False,
            alignment_explanation=(
                "Store inventory strongly aligns with West India demand patterns. "
                "5 of 7 primary regional categories detected. "
                "High turnover probability for regionally-demanded products. Factor: +1.02x."
            ),
        ),
        economic_estimate=EconomicEstimate(
            daily_sales_low=6000,
            daily_sales_mid=7500,
            daily_sales_high=9000,
            monthly_revenue_low=168000,
            monthly_revenue_mid=210000,
            monthly_revenue_high=252000,
            monthly_income_low=20160,
            monthly_income_mid=25200,
            monthly_income_high=30240,
            confidence_score=0.74,
            range_width_percent=0.25,
            base_rate_used=7000,
            vision_multiplier_applied=1.10,
            geo_multiplier_applied=1.08,
            competition_adjustment_applied=1.10,
            stability_factor_applied=1.05,
            demand_alignment_factor_applied=1.02,
            combined_multiplier=1.07,
            formula_explanation=(
                "Base Rs.7,000/day (TIER_2, SMALL) "
                "x Vision 1.10 x Geo 1.08 x Competition 1.10 "
                "x Stability 1.05 x Demand Alignment 1.02 "
                "= Combined 1.40x -> Clamped 1.07x -> Rs.7,500/day"
            ),
        ),
        fraud_analysis=FraudAnalysis(
            manipulation_probability=0.08,
            risk_flags=[
                RiskFlag(
                    flag_type="NOTE_COMPETITION",
                    severity="LOW",
                    confidence=0.40,
                    evidence="5 competing stores within 500m suggests moderate market saturation.",
                    recommendation="NOTE_FOR_RECORD",
                ),
            ],
            consistency_assessment=(
                "All visual and geospatial signals are mutually consistent. "
                "SDI of 0.78 aligns well with SMALL store in TIER_2 Pune. "
                "Stability and regional demand signals corroborate genuine, mature operation."
            ),
            recommendation="APPROVE",
            recommendation_rationale=(
                "Store profile is consistent across all signal dimensions. "
                "5-year operation history with active inventory turnover supports creditworthiness."
            ),
            llm_reasoning_available=False,
        ),
        loan_recommendation=LoanRecommendation(
            recommendation="PRE_APPROVE",
            recommendation_label="Pre-Approve (Subject to KYC)",
            eligible_loan_low=180000,
            eligible_loan_high=240000,
            recommended_tenure_months_low=12,
            recommended_tenure_months_high=18,
            emi_range_low=11000,
            emi_range_high=16000,
        ),
        recommendation="APPROVE",
        recommendation_rationale=(
            "Store profile is consistent across all signal dimensions. "
            "5-year operation history supports creditworthiness."
        ),
        human_readable_report=(
            "CREDIT ASSESSMENT REPORT -- KiranaLens v4.0\n"
            "==================================================\n\n"
            "STORE PROFILE: SMALL kirana store (~180 sqft) in TIER_2 zone, West India (Pune). "
            "Computer vision detected 252 products across 6 categories with SDI of 0.78.\n\n"
            "CATEGORY INTELLIGENCE: 6 retail categories identified via COCO+spatial inference. "
            "Primary: Packaged Foods (128), Beverages (42), Personal Care (26). "
            "SKU diversity: High (0.72). Est. inventory value: Rs.68,500 (Medium).\n\n"
            "REVENUE ESTIMATE: Daily revenue range Rs.6,000 - Rs.9,000 (midpoint Rs.7,500/day). "
            "Monthly revenue Rs.1,68,000 - Rs.2,52,000. "
            "Estimated monthly net income: Rs.25,200. Confidence: 74%.\n\n"
            "OPERATIONAL INDICATORS: Stability grade is HIGH (score: 0.76, factor: 1.05x). "
            "Regional demand alignment is STRONG (score: 0.74). "
            "Store demonstrates mature, consistent operations with 5 years of history.\n\n"
            "RISK ASSESSMENT: Manipulation probability 8%. "
            "1 risk flag identified (low severity -- competition note). "
            "No significant concerns detected.\n\n"
            "LOAN RECOMMENDATION: PRE-APPROVE. "
            "Eligible loan: Rs.1,80,000 - Rs.2,40,000. Tenure: 12-18 months. "
            "EMI range: Rs.11,000 - Rs.16,000.\n\n"
            "RECOMMENDATION: APPROVE. "
            "Store profile is consistent and creditworthy."
        ),
        processing_time_seconds=87.4,
        model_version="KL-v4.0",
    ).model_dump()


@router.post("/assess")
async def run_assessment(
    images: list[UploadFile] = File(...),
    lat: float = Form(...),
    lng: float = Form(...),
    shop_name: str = Form(default="Unknown Store"),
    years_in_operation: int = Form(default=0),
):
    """
    Full assessment pipeline.
    Accepts 3-5 shop images + GPS coordinates.
    Returns structured cash flow estimate + confidence score + fraud flags.
    """
    t0 = time.time()
    assessment_id = f"KL-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    # --- Input Validation ---
    if len(images) < 1:
        raise HTTPException(status_code=400, detail="At least 1 image required (3-5 recommended)")
    if len(images) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")
    if not (6.0 <= lat <= 38.0):
        raise HTTPException(status_code=400, detail=f"Latitude {lat} is outside India bounds (6-38)")
    if not (68.0 <= lng <= 98.0):
        raise HTTPException(status_code=400, detail=f"Longitude {lng} is outside India bounds (68-98)")

    # --- Save uploaded images to temp dir ---
    temp_dir = tempfile.mkdtemp(prefix="kiranalens_")
    image_paths = []
    try:
        for idx, img_file in enumerate(images):
            ext = os.path.splitext(img_file.filename or "img.jpg")[1] or ".jpg"
            path = os.path.join(temp_dir, f"img_{idx}{ext}")
            content = await img_file.read()
            with open(path, "wb") as f:
                f.write(content)
            image_paths.append(path)
            logger.info(f"Saved image {idx+1}: {path} ({len(content)} bytes)")

        # === PIPELINE EXECUTION ===

        # Step 1: Vision extraction (now includes category intelligence)
        from app.services.vision_service import extract_vision_features
        logger.info("Step 1/8: Vision extraction + Category Intelligence...")
        vision = extract_vision_features(image_paths)
        logger.info(f"Vision: SDI={vision.sdi}, products={vision.total_products_detected}, categories={len(vision.category_counts)}")

        # Step 2: Geo features
        from app.services.geo_service import get_geo_features
        logger.info("Step 2/8: Geo features...")
        geo = get_geo_features(lat, lng)
        logger.info(f"Geo: tier={geo.city_tier}, region={geo.india_region}, footfall={geo.footfall_proxy_index}")

        # Step 3: Operational Stability
        from app.services.stability_service import compute_operational_stability
        logger.info("Step 3/8: Operational stability...")
        stability = compute_operational_stability(
            sdi=vision.sdi,
            sdi_variance=vision.sdi_variance,
            refill_signal=vision.refill_signal,
            visual_organisation_score=vision.visual_organisation_score,
            inventory_density_score=vision.inventory_density_score,
            years_in_operation=years_in_operation,
        )
        logger.info(f"Stability: grade={stability.stability_grade}, factor={stability.stability_factor}")

        # Step 4: Regional Demand Alignment
        from app.services.regional_demand_service import compute_regional_demand_alignment
        logger.info("Step 4/8: Regional demand alignment...")
        regional = compute_regional_demand_alignment(
            lat=lat, lng=lng,
            detected_categories=vision.detected_categories,
            india_region=geo.india_region,
        )
        logger.info(f"Regional: grade={regional.alignment_grade}, factor={regional.demand_alignment_factor}")

        # Step 5: Confidence
        from app.services.economic_engine import compute_confidence
        logger.info("Step 5/8: Confidence scoring...")
        signal_consistency = max(0.1, 1.0 - abs(vision.sdi - geo.footfall_proxy_index))
        confidence = compute_confidence(
            image_count=len(images),
            image_quality=vision.overall_image_quality,
            sdi_confidence=vision.sdi_confidence,
            geo_data_confidence=geo.data_confidence,
            signal_consistency=signal_consistency,
            stability_score=stability.stability_score,
            alignment_score=regional.regional_alignment_score,
        )
        logger.info(f"Confidence: {confidence}")

        # Step 6: Economic estimate
        from app.services.economic_engine import compute_estimate
        logger.info("Step 6/8: Economic estimate...")
        estimate = compute_estimate(
            city_tier=geo.city_tier,
            store_size=vision.store_size_proxy,
            vision_mult=vision.vision_multiplier,
            geo_mult=geo.geo_multiplier,
            comp_adj=geo.competition_adjustment,
            stability_factor=stability.stability_factor,
            demand_alignment_factor=regional.demand_alignment_factor,
            confidence=confidence,
            total_products_detected=vision.total_products_detected
        )
        logger.info(f"Estimate: daily_mid=Rs.{estimate.daily_sales_mid:,}, combined={estimate.combined_multiplier}")

        # Step 7: Fraud detection -- rules first, then LLM
        from app.services.hf_service import rule_based_fraud_prescreening, analyze_fraud, generate_report
        logger.info("Step 7/8: Fraud detection...")

        combined_features = {
            **vision.model_dump(exclude={"annotated_image_b64"}),
            **geo.model_dump(),
            **estimate.model_dump(),
            "stability_score": stability.stability_score,
            "stability_grade": stability.stability_grade,
            "stability_factor": stability.stability_factor,
            "possible_initial_stocking": stability.possible_initial_stocking,
            "stability_explanation": stability.stability_explanation,
            "regional_alignment_score": regional.regional_alignment_score,
            "alignment_grade": regional.alignment_grade,
            "expected_categories": regional.expected_categories,
            "detected_matching": regional.detected_matching,
            "detected_missing": regional.detected_missing,
            "demand_mismatch": regional.demand_mismatch,
            "india_region": regional.india_region,
        }

        rule_flags = rule_based_fraud_prescreening(combined_features)
        llm_fraud = await analyze_fraud(combined_features)

        # Merge flags (deduplicate by flag_type)
        rule_flag_types = {r["flag_type"] for r in rule_flags}
        all_flags_raw = rule_flags + [
            f for f in llm_fraud.get("risk_flags", [])
            if f.get("flag_type") not in rule_flag_types
        ]

        manipulation_prob = max(
            len(rule_flags) * 0.15,
            llm_fraud.get("manipulation_probability", 0.05)
        )
        manipulation_prob = round(min(manipulation_prob, 1.0), 2)

        # Determine final recommendation
        high_flags = [f for f in all_flags_raw if f.get("severity") == "HIGH"]
        if manipulation_prob > 0.60 or len(high_flags) >= 2:
            final_rec = "REJECT"
        elif manipulation_prob > 0.25 or len(high_flags) >= 1 or len(all_flags_raw) >= 3:
            final_rec = "VERIFY"
        else:
            final_rec = "APPROVE"

        # Convert flags to RiskFlag models
        risk_flags = []
        for f in all_flags_raw:
            try:
                risk_flags.append(RiskFlag(**f))
            except Exception:
                risk_flags.append(RiskFlag(
                    flag_type=f.get("flag_type", "UNKNOWN"),
                    severity=f.get("severity", "LOW"),
                    confidence=f.get("confidence", 0.5),
                    evidence=f.get("evidence", "See detailed analysis"),
                    recommendation=f.get("recommendation", "NOTE_FOR_RECORD"),
                ))

        fraud_result = FraudAnalysis(
            manipulation_probability=manipulation_prob,
            risk_flags=risk_flags,
            consistency_assessment=llm_fraud.get("consistency_assessment", "Rule-based analysis completed."),
            recommendation=final_rec,
            recommendation_rationale=llm_fraud.get("recommendation_rationale", f"Based on {len(all_flags_raw)} detected signals."),
            llm_reasoning_available=llm_fraud.get("llm_reasoning_available", False),
        )

        # Step 7.5: Loan Recommendation (NEW v4.0)
        from app.services.economic_engine import compute_loan_recommendation
        loan_rec = compute_loan_recommendation(
            monthly_income_mid=estimate.monthly_income_mid,
            confidence_score=confidence,
            manipulation_probability=manipulation_prob,
            risk_flags=all_flags_raw,
        )

        # Step 8: Report generation
        logger.info("Step 8/8: Report generation...")
        report = await generate_report(combined_features, estimate.model_dump(), {
            "manipulation_probability": manipulation_prob,
            "risk_flags": all_flags_raw,
            "recommendation": final_rec,
        })

        processing_time = round(time.time() - t0, 2)
        logger.info(f"Assessment {assessment_id} completed in {processing_time}s -> {final_rec}")

        return AssessmentResponse(
            assessment_id=assessment_id,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            status="COMPLETE",
            inputs={
                "shop_name": shop_name,
                "lat": lat,
                "lng": lng,
                "images_count": len(images),
                "years_in_operation": years_in_operation,
            },
            vision_features=vision,
            geo_features=geo,
            operational_stability=stability,
            regional_demand=regional,
            economic_estimate=estimate,
            fraud_analysis=fraud_result,
            loan_recommendation=loan_rec,
            recommendation=final_rec,
            recommendation_rationale=fraud_result.recommendation_rationale,
            human_readable_report=report,
            processing_time_seconds=processing_time,
            model_version="KL-v4.0",
        ).model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assessment pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")
    finally:
        # Cleanup temp files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
