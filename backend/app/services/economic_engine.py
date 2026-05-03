# backend/app/services/economic_engine.py
"""
KiranaLens v3.0 — Economic Model Engine.
Computes estimated daily/monthly sales and income from 6 multiplied factors.

Formula:
  Estimated Daily Sales = Base Rate(city_tier, store_size)
    x Vision Multiplier      [0.40 - 1.80]
    x Geo Multiplier         [0.50 - 1.60]
    x Competition Adjustment  [0.70 - 1.20]
    x Stability Factor        [0.85 - 1.15]  <- NEW v3.0
    x Demand Alignment Factor [0.90 - 1.10]  <- NEW v3.0

All base rates are sourced from FMCG industry reports on Indian kirana economics.
"""

import logging
from app.models.schemas import EconomicEstimate

logger = logging.getLogger(__name__)

# ============================================================================
# Base Rate Lookup Table (INR/day)
# (city_tier, store_size) -> (low, mid, high) daily sales in INR
# Sourced from: RedSeer/Redseer FMCG kirana economics + BCG India reports
# ============================================================================
BASE_RATES = {
    # TIER_1: Metro cities (Mumbai, Delhi, Bangalore, etc.)
    ("TIER_1", "LARGE"):  (12000, 18000, 28000),
    ("TIER_1", "MEDIUM"): (7000, 11000, 17000),
    ("TIER_1", "SMALL"):  (4000, 7000, 11000),
    ("TIER_1", "MICRO"):  (2000, 3500, 5500),

    # TIER_2: Large cities (Dehradun, Shimla, Mysore, etc.)
    ("TIER_2", "LARGE"):  (8000, 13000, 20000),
    ("TIER_2", "MEDIUM"): (5000, 8000, 13000),
    ("TIER_2", "SMALL"):  (3000, 5000, 8000),
    ("TIER_2", "MICRO"):  (1500, 2500, 4000),

    # TIER_3: Small cities / large towns
    ("TIER_3", "LARGE"):  (5000, 9000, 14000),
    ("TIER_3", "MEDIUM"): (3000, 5500, 9000),
    ("TIER_3", "SMALL"):  (2000, 3500, 6000),
    ("TIER_3", "MICRO"):  (800, 1500, 2800),


}

OPERATING_DAYS = 28  # typical kirana operates ~28 days/month
NET_MARGIN = 0.12    # typical kirana net margin: 10-15%


def compute_confidence(
    image_count: int,
    image_quality: float,
    sdi_confidence: float,
    geo_data_confidence: float,
    signal_consistency: float,
    stability_score: float,
    alignment_score: float,
) -> float:
    """
    Compute overall confidence score [0.10, 1.00].
    More images, higher quality, more consistent signals = higher confidence.
    """
    img_factor = min(image_count / 5.0, 1.0)
    raw = (
        img_factor            * 0.12 +
        image_quality         * 0.20 +
        sdi_confidence        * 0.20 +
        geo_data_confidence   * 0.15 +
        signal_consistency    * 0.13 +
        stability_score       * 0.10 +
        alignment_score       * 0.10
    )
    return round(max(0.10, min(1.00, raw)), 3)


def compute_estimate(
    city_tier: str,
    store_size: str,
    vision_mult: float,
    geo_mult: float,
    comp_adj: float,
    stability_factor: float,
    demand_alignment_factor: float,
    confidence: float,
    total_products_detected: int = 0,
) -> EconomicEstimate:
    """
    Compute economic estimate using the 6-factor formula.
    Returns structured estimate with full audit trail.
    """
    # Ensure UNKNOWN maps safely
    if city_tier == "UNKNOWN" or city_tier not in ["TIER_1", "TIER_2", "TIER_3"]:
        city_tier = "TIER_3"

    key = (city_tier, store_size)
    if key not in BASE_RATES:
        logger.warning(f"Missing base rate for {key}. Defaulting to TIER_3, SMALL.")
        base_low, base_mid, base_high = BASE_RATES[("TIER_3", "SMALL")]
    else:
        base_low, base_mid, base_high = BASE_RATES[key]

    # Combined multiplier -- hard cap [0.30, 2.80]
    combined_raw = vision_mult * geo_mult * comp_adj * stability_factor * demand_alignment_factor

    # [MODIFIED] Heuristic floor
    if total_products_detected > 100:
        combined_raw = max(0.95, combined_raw)  # Very stocked stores shouldn't fail
    elif total_products_detected > 40:
        combined_raw = max(0.70, combined_raw)

    # 🔥 FINAL CLAMP - increased the absolute floor to 0.50
    combined = round(max(0.50, min(1.80, combined_raw)), 3)

    daily_mid = int(base_mid * combined)

    # Range width from confidence
    if confidence >= 0.85:
        range_pct = 0.15
    elif confidence >= 0.65:
        range_pct = 0.25
    elif confidence >= 0.45:
        range_pct = 0.40
    else:
        range_pct = 0.60

    daily_low = max(int(daily_mid * (1 - range_pct)), int(base_low * combined * 0.85))
    daily_high = min(int(daily_mid * (1 + range_pct)), int(base_high * combined * 1.15))

    # Ensure low < mid < high
    daily_low = min(daily_low, daily_mid - 1) if daily_low >= daily_mid else daily_low
    daily_high = max(daily_high, daily_mid + 1) if daily_high <= daily_mid else daily_high

    # [NEW] Prevent absurdly low final estimates
    daily_low = max(daily_low, 800)
    daily_mid = max(daily_mid, 1200)
    daily_high = max(daily_high, 1800)

    def monthly(d: int) -> int:
        return d * OPERATING_DAYS

    def income(r: int) -> int:
        return int(r * NET_MARGIN)

    explanation = (
        f"Base Rs.{base_mid:,}/day ({city_tier}, {store_size}) "
        f"x Vision {vision_mult:.2f} x Geo {geo_mult:.2f} x Competition {comp_adj:.2f} "
        f"x Stability {stability_factor:.2f} x Demand Alignment {demand_alignment_factor:.2f} "
        f"= Raw {combined_raw:.2f}x → Clamped {combined:.2f}x -> Rs.{daily_mid:,}/day"
    )

    logger.info(f"Economic estimate: base={base_mid}, combined={combined}, daily_mid={daily_mid}")

    return EconomicEstimate(
        daily_sales_low=daily_low,
        daily_sales_mid=daily_mid,
        daily_sales_high=daily_high,
        monthly_revenue_low=monthly(daily_low),
        monthly_revenue_mid=monthly(daily_mid),
        monthly_revenue_high=monthly(daily_high),
        monthly_income_low=income(monthly(daily_low)),
        monthly_income_mid=income(monthly(daily_mid)),
        monthly_income_high=income(monthly(daily_high)),
        confidence_score=confidence,
        range_width_percent=range_pct,
        base_rate_used=base_mid,
        vision_multiplier_applied=vision_mult,
        geo_multiplier_applied=geo_mult,
        competition_adjustment_applied=comp_adj,
        stability_factor_applied=stability_factor,
        demand_alignment_factor_applied=demand_alignment_factor,
        combined_multiplier=combined,
        formula_explanation=explanation,
    )


def compute_loan_recommendation(
    monthly_income_mid: int,
    confidence_score: float,
    manipulation_probability: float,
    risk_flags: list,
) -> "LoanRecommendation":
    """
    Simple loan eligibility calculation.
    NBFC rule of thumb: loan amount = 4-7x monthly income
    EMI should not exceed 40% of monthly income.
    """
    from app.models.schemas import LoanRecommendation

    # Hard reject conditions
    high_severity_flags = [f for f in risk_flags if isinstance(f, dict) and f.get("severity") == "HIGH"]
    if manipulation_probability > 0.40 or len(high_severity_flags) > 1:
        return LoanRecommendation(
            recommendation="REJECT",
            recommendation_label="Not Recommended for Lending",
            eligible_loan_low=0,
            eligible_loan_high=0,
            recommended_tenure_months_low=0,
            recommended_tenure_months_high=0,
            emi_range_low=0,
            emi_range_high=0,
        )

    # Compute loan amounts
    multiplier_low = 4 if confidence_score < 0.65 else 5
    multiplier_high = 5 if confidence_score < 0.65 else 7

    loan_low = int(monthly_income_mid * multiplier_low / 1000) * 1000
    loan_high = int(monthly_income_mid * multiplier_high / 1000) * 1000

    # Ensure minimums
    loan_low = max(loan_low, 10000)
    loan_high = max(loan_high, loan_low + 10000)

    tenure_low = 12
    tenure_high = 18 if confidence_score >= 0.70 else 12

    # EMI calculation (simple division, no interest for estimate)
    emi_low = max(int(loan_low / tenure_high / 100) * 100, 1000)
    emi_high = max(int(loan_high / tenure_low / 100) * 100, emi_low + 1000)

    # Determine recommendation
    if manipulation_probability > 0.20 or len(risk_flags) > 2:
        rec = "VERIFY"
        rec_label = "Manual Verification Required"
    else:
        rec = "PRE_APPROVE"
        rec_label = "Pre-Approve (Subject to KYC)"

    return LoanRecommendation(
        recommendation=rec,
        recommendation_label=rec_label,
        eligible_loan_low=loan_low,
        eligible_loan_high=loan_high,
        recommended_tenure_months_low=tenure_low,
        recommended_tenure_months_high=tenure_high,
        emi_range_low=emi_low,
        emi_range_high=emi_high,
    )

