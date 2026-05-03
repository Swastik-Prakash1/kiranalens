# backend/tests/test_regional_demand.py
"""Tests for Regional Demand Alignment Signal -- KiranaLens v3.0"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.regional_demand_service import compute_regional_demand_alignment


def test_north_india_aligned():
    """Store in Delhi with typical north India products."""
    result = compute_regional_demand_alignment(
        lat=28.61, lng=77.20,
        detected_categories=["bulk_staples", "beverages_bottles", "packaged_snacks",
                              "personal_care_items", "general_fmcg"],
        india_region="north_india"
    )
    assert result.india_region == "north_india"
    assert result.regional_alignment_score >= 0.40
    assert 0.90 <= result.demand_alignment_factor <= 1.10
    print(f"[OK] North India: score={result.regional_alignment_score}, grade={result.alignment_grade}")


def test_south_india_aligned():
    """Store in Chennai with typical south India products."""
    result = compute_regional_demand_alignment(
        lat=13.08, lng=80.27,
        detected_categories=["tall_narrow_items", "beverages_bottles", "spices_condiments",
                              "bulk_staples", "packaged_snacks"],
        india_region="south_india"
    )
    assert result.india_region == "south_india"
    assert 0.90 <= result.demand_alignment_factor <= 1.10
    print(f"[OK] South India: score={result.regional_alignment_score}, grade={result.alignment_grade}")


def test_demand_mismatch_triggers():
    """South India store with zero south-India specific products -- should flag mismatch."""
    result = compute_regional_demand_alignment(
        lat=13.08, lng=80.27,
        detected_categories=["tall_narrow_items"],  # almost nothing detected
        india_region="south_india"
    )
    # Should detect low alignment
    assert result.regional_alignment_score < 0.50, f"Expected low alignment, got {result.regional_alignment_score}"
    print(f"[OK] Mismatch detected: score={result.regional_alignment_score}, mismatch={result.demand_mismatch}")


def test_output_bounds_all_regions():
    """Verify output bounds for all 5 regions."""
    regions = ["north_india", "south_india", "east_india", "west_india", "central_india"]
    cats = ["packaged_snacks", "beverages_bottles", "bulk_staples"]
    for r in regions:
        result = compute_regional_demand_alignment(
            lat=20.0, lng=78.0,
            detected_categories=cats, india_region=r
        )
        assert 0.0 <= result.regional_alignment_score <= 1.0
        assert 0.90 <= result.demand_alignment_factor <= 1.10
        assert result.alignment_grade in ["STRONG", "MODERATE", "WEAK"]
        print(f"[OK] {r}: score={result.regional_alignment_score}, factor={result.demand_alignment_factor}")


def test_empty_categories():
    """Store with no detected categories -- should give weak alignment."""
    result = compute_regional_demand_alignment(
        lat=20.0, lng=78.0,
        detected_categories=[],
        india_region="central_india"
    )
    assert result.regional_alignment_score == 0.0
    assert result.demand_alignment_factor == 0.90
    assert result.alignment_grade == "WEAK"
    assert result.demand_mismatch is True
    print(f"[OK] Empty categories: score={result.regional_alignment_score}, mismatch={result.demand_mismatch}")
