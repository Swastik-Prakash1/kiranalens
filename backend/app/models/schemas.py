# backend/app/models/schemas.py
"""
KiranaLens v4.0 — Pydantic data models for the entire pipeline.
Every service imports from this file. No duplicates.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class VisionFeatures(BaseModel):
    sdi: float = Field(..., ge=0.0, le=1.0)
    sdi_confidence: float = Field(..., ge=0.0, le=1.0)
    sdi_variance: float  # variance across images — key for stability signal
    sku_diversity_count: int = Field(..., ge=0)
    detected_categories: list[str]
    inventory_density_score: float = Field(..., ge=0.0, le=1.0)
    refill_signal: str  # RECENT_RESTOCK | NORMAL | LOW_STOCK | STAGED
    visual_organisation_score: float = Field(..., ge=0.0, le=1.0)  # NEW v3.0
    store_size_proxy: str  # MICRO | SMALL | MEDIUM | LARGE
    estimated_floor_area_sqft: int
    total_products_detected: int
    shelf_regions_detected: int
    image_quality_scores: list[float]
    overall_image_quality: float = Field(..., ge=0.0, le=1.0)
    vision_multiplier: float = Field(..., ge=0.4, le=1.8)
    processing_notes: list[str]

    # ── v4.0 Category Intelligence fields ──────────────────────────────────
    category_counts: dict[str, int] = Field(default_factory=dict)
    sku_diversity_score: float = 0.0
    sku_diversity_label: str = "Low"
    estimated_inventory_value_inr: int = 0
    inventory_value_band: str = "Low"
    business_insight: str = ""
    category_risk_flags: list[str] = Field(default_factory=list)
    coco_detections_used: int = 0
    detection_method: str = "spatial_only"
    annotated_image_b64: Optional[str] = None


class GeoFeatures(BaseModel):
    lat: float
    lng: float
    city_tier: str
    india_region: str  # NEW v3.0: north_india|south_india|east_india|west_india|central_india
    road_type: str
    road_type_score: float = Field(..., ge=0.0, le=1.0)
    nearby_amenities: dict
    amenity_score: float = Field(..., ge=0.0, le=1.0)
    competition_count_300m: int = Field(..., ge=0)
    competition_count_500m: int = Field(..., ge=0)
    competition_density_score: float = Field(..., ge=0.0, le=1.0)
    competition_adjustment: float = Field(..., ge=0.7, le=1.2)
    catchment_density_score: float = Field(..., ge=0.0, le=1.0)
    footfall_proxy_index: float = Field(..., ge=0.0, le=1.0)
    geo_multiplier: float = Field(..., ge=0.5, le=1.6)
    data_confidence: float = Field(..., ge=0.0, le=1.0)
    fallback_used: bool


class OperationalStabilityResult(BaseModel):  # NEW v3.0
    stability_score: float = Field(..., ge=0.0, le=1.0)
    stability_factor: float = Field(..., ge=0.85, le=1.15)
    stability_grade: str  # HIGH | MEDIUM | LOW
    possible_initial_stocking: bool
    stability_explanation: str
    signals_used: dict  # transparency dict of inputs and their contribution


class RegionalDemandResult(BaseModel):  # NEW v3.0
    india_region: str
    regional_alignment_score: float = Field(..., ge=0.0, le=1.0)
    demand_alignment_factor: float = Field(..., ge=0.90, le=1.10)
    alignment_grade: str  # STRONG | MODERATE | WEAK
    expected_categories: list[str]
    detected_matching: list[str]
    detected_missing: list[str]
    demand_mismatch: bool
    alignment_explanation: str


class EconomicEstimate(BaseModel):
    daily_sales_low: int
    daily_sales_mid: int
    daily_sales_high: int
    monthly_revenue_low: int
    monthly_revenue_mid: int
    monthly_revenue_high: int
    monthly_income_low: int
    monthly_income_mid: int
    monthly_income_high: int
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    range_width_percent: float
    base_rate_used: int
    vision_multiplier_applied: float
    geo_multiplier_applied: float
    competition_adjustment_applied: float
    stability_factor_applied: float       # NEW v3.0
    demand_alignment_factor_applied: float  # NEW v3.0
    combined_multiplier: float
    formula_explanation: str


class RiskFlag(BaseModel):
    flag_type: str
    severity: str  # HIGH | MEDIUM | LOW
    confidence: float
    evidence: str
    recommendation: str  # REJECT | MANUAL_VERIFY | NOTE_FOR_RECORD


class FraudAnalysis(BaseModel):
    manipulation_probability: float = Field(..., ge=0.0, le=1.0)
    risk_flags: list[RiskFlag]
    consistency_assessment: str
    recommendation: str  # APPROVE | VERIFY | REJECT
    recommendation_rationale: str
    llm_reasoning_available: bool


class LoanRecommendation(BaseModel):
    """v4.0 — Loan eligibility recommendation."""
    recommendation: str  # PRE_APPROVE | VERIFY | REJECT
    recommendation_label: str
    eligible_loan_low: int = 0
    eligible_loan_high: int = 0
    recommended_tenure_months_low: int = 0
    recommended_tenure_months_high: int = 0
    emi_range_low: int = 0
    emi_range_high: int = 0


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    assessment_id: str
    timestamp_utc: str
    status: str
    inputs: dict
    vision_features: VisionFeatures
    geo_features: GeoFeatures
    operational_stability: OperationalStabilityResult   # NEW v3.0
    regional_demand: RegionalDemandResult               # NEW v3.0
    economic_estimate: EconomicEstimate
    fraud_analysis: FraudAnalysis
    loan_recommendation: LoanRecommendation             # NEW v4.0
    recommendation: str
    recommendation_rationale: str
    human_readable_report: str
    processing_time_seconds: float
    model_version: str = "KL-v4.0"
