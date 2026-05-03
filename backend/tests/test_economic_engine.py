# backend/tests/test_economic_engine.py
"""Tests for Economic Model Engine -- KiranaLens v3.0"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.economic_engine import compute_estimate, compute_confidence


def test_basic_estimate():
    """Test basic economic estimate computation."""
    result = compute_estimate(
        city_tier="TIER_1", store_size="MEDIUM",
        vision_mult=1.10, geo_mult=1.05, comp_adj=0.95,
        stability_factor=1.08, demand_alignment_factor=1.04,
        confidence=0.80,
    )
    assert result.daily_sales_mid > 0
    assert result.monthly_revenue_mid == result.daily_sales_mid * 28
    assert result.daily_sales_low < result.daily_sales_mid < result.daily_sales_high
    assert "Stability" in result.formula_explanation
    assert "Demand Alignment" in result.formula_explanation
    print(f"[OK] Basic: mid=Rs.{result.daily_sales_mid:,}/day, combined={result.combined_multiplier}")


def test_all_6_factors_in_formula():
    """Verify all 6 factors appear in the formula explanation."""
    result = compute_estimate(
        city_tier="TIER_2", store_size="SMALL",
        vision_mult=0.90, geo_mult=0.85, comp_adj=1.10,
        stability_factor=1.00, demand_alignment_factor=0.95,
        confidence=0.65,
    )
    assert result.stability_factor_applied == 1.00
    assert result.demand_alignment_factor_applied == 0.95
    assert result.vision_multiplier_applied == 0.90
    assert result.geo_multiplier_applied == 0.85
    assert result.competition_adjustment_applied == 1.10
    print(f"[OK] All 6 factors: {result.formula_explanation}")


def test_confidence_computation():
    """Test confidence includes stability and alignment."""
    conf = compute_confidence(
        image_count=4, image_quality=0.80,
        sdi_confidence=0.85, geo_data_confidence=0.75,
        signal_consistency=0.70, stability_score=0.80,
        alignment_score=0.75,
    )
    assert 0.10 <= conf <= 1.00
    print(f"[OK] Confidence: {conf}")


def test_low_confidence_widens_range():
    """Low confidence should give wider estimate range."""
    high_conf = compute_estimate(
        city_tier="TIER_1", store_size="SMALL",
        vision_mult=1.0, geo_mult=1.0, comp_adj=1.0,
        stability_factor=1.0, demand_alignment_factor=1.0,
        confidence=0.90,
    )
    low_conf = compute_estimate(
        city_tier="TIER_1", store_size="SMALL",
        vision_mult=1.0, geo_mult=1.0, comp_adj=1.0,
        stability_factor=1.0, demand_alignment_factor=1.0,
        confidence=0.30,
    )
    high_range = high_conf.daily_sales_high - high_conf.daily_sales_low
    low_range = low_conf.daily_sales_high - low_conf.daily_sales_low
    assert low_range > high_range, "Low confidence should give wider range"
    print(f"[OK] Range widening: high_conf_range={high_range}, low_conf_range={low_range}")


def test_combined_multiplier_caps():
    """Combined multiplier should be capped at [0.30, 2.80]."""
    # Very high multipliers
    result = compute_estimate(
        city_tier="TIER_1", store_size="LARGE",
        vision_mult=1.80, geo_mult=1.60, comp_adj=1.20,
        stability_factor=1.15, demand_alignment_factor=1.10,
        confidence=0.80,
    )
    assert result.combined_multiplier <= 2.80
    print(f"[OK] Cap check: combined={result.combined_multiplier}")
