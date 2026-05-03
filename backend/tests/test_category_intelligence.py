# backend/tests/test_category_intelligence.py
"""
KiranaLens v4.0 — Unit tests for Category Intelligence Layer.
All tests are pure logic — no YOLO model loading needed.
"""

import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.category_intelligence import (
    run_category_intelligence,
    compute_sku_diversity_score,
    compute_inventory_value,
    compute_enhanced_refill_signal,
    generate_business_insight,
    compute_risk_flags,
    classify_zone,
    COCO_TO_RETAIL_CATEGORY,
    ZONE_CATEGORY_MAP,
    CATEGORY_AVG_PRICE_INR,
)


def test_coco_mapping_complete():
    """Every COCO class in the map should produce a valid category."""
    for coco_class, category in COCO_TO_RETAIL_CATEGORY.items():
        assert isinstance(category, str), f"Category for '{coco_class}' is not a string"
        assert len(category) > 0, f"Category for '{coco_class}' is empty"
        assert category in CATEGORY_AVG_PRICE_INR, (
            f"Category '{category}' mapped from '{coco_class}' not in price table"
        )
    print(f"[PASS] {len(COCO_TO_RETAIL_CATEGORY)} COCO mappings valid")


def test_zone_category_map_complete():
    """Every zone should map to valid categories."""
    for zone, cats in ZONE_CATEGORY_MAP.items():
        assert len(cats) > 0, f"Zone '{zone}' has no categories"
        for cat in cats:
            assert cat in CATEGORY_AVG_PRICE_INR, (
                f"Zone '{zone}' category '{cat}' not in price table"
            )
    print(f"[PASS] {len(ZONE_CATEGORY_MAP)} zones all map to valid categories")


def test_classify_zone():
    """Zone classification should be correct for various y positions."""
    assert classify_zone(50, 1000) == "top"
    assert classify_zone(250, 1000) == "upper"
    assert classify_zone(450, 1000) == "middle"
    assert classify_zone(650, 1000) == "lower"
    assert classify_zone(900, 1000) == "bottom"
    print("[PASS] Zone classification correct for all positions")


def test_sku_diversity_score_bounds():
    """SKU diversity score must always be [0, 1]."""
    for n in range(0, 20):
        score, label = compute_sku_diversity_score(n)
        assert 0.0 <= score <= 1.0, f"Score out of bounds for n={n}: {score}"
        assert label in ("None", "Low", "Medium", "High", "Very High"), (
            f"Invalid label '{label}' for n={n}"
        )
    print("[PASS] SKU diversity scores all in bounds [0, 1]")


def test_sku_diversity_monotonic():
    """More categories should always give higher or equal score."""
    prev_score = -1.0
    for n in range(0, 15):
        score, _ = compute_sku_diversity_score(n)
        assert score >= prev_score, (
            f"Score decreased from n={n-1} to n={n}: {prev_score} -> {score}"
        )
        prev_score = score
    print("[PASS] SKU diversity scores are monotonically increasing")


def test_inventory_value_calculation():
    """Inventory value should be exact arithmetic."""
    cats = {"Packaged Foods": 100, "Beverages": 42, "Personal Care": 20}
    value, band = compute_inventory_value(cats)
    # 100×30 + 42×40 + 20×55 = 3000 + 1680 + 1100 = 5780 → Very Low
    assert value == 5780, f"Expected 5780, got {value}"
    assert band == "Very Low", f"Expected 'Very Low', got '{band}'"
    print(f"[PASS] Inventory value: Rs.{value:,} = {band}")


def test_inventory_value_bands():
    """Test all inventory value bands."""
    # Very Low
    _, band = compute_inventory_value({"Packaged Foods": 10})
    assert band == "Very Low"

    # Low
    _, band = compute_inventory_value({"Packaged Foods": 700})
    assert band == "Low"

    # Medium
    _, band = compute_inventory_value({"Beverages": 1500})
    assert band == "Medium"

    # High
    _, band = compute_inventory_value({"Electronics": 250})
    assert band == "High"

    # Very High
    _, band = compute_inventory_value({"Electronics": 500})
    assert band == "Very High"

    print("[PASS] All inventory value bands verified")


def test_refill_signal_high_sdi_uniform():
    """Very high SDI with low variance should flag STAGED."""
    signal, score = compute_enhanced_refill_signal(
        sdi=0.92, sdi_variance=0.01, total_products=120,
        img_height=640, boxes=[],
    )
    assert signal == "STAGED", f"Expected STAGED for uniform high SDI, got {signal}"
    print(f"[PASS] Staged detection: signal={signal}, score={score}")


def test_refill_signal_high_sdi_variable():
    """High SDI with variance should flag RECENT_RESTOCK."""
    signal, score = compute_enhanced_refill_signal(
        sdi=0.85, sdi_variance=0.08, total_products=100,
        img_height=640, boxes=[],
    )
    assert signal == "RECENT_RESTOCK", f"Expected RECENT_RESTOCK, got {signal}"
    print(f"[PASS] Recent restock detection: signal={signal}, score={score}")


def test_refill_signal_low_sdi():
    """Low SDI should flag LOW_STOCK."""
    signal, score = compute_enhanced_refill_signal(
        sdi=0.20, sdi_variance=0.02, total_products=15,
        img_height=640, boxes=[],
    )
    assert signal == "LOW_STOCK", f"Expected LOW_STOCK, got {signal}"
    print(f"[PASS] Low stock detection: signal={signal}, score={score}")


def test_business_insight_generated():
    """Business insight should be non-empty and contain key terms."""
    insight = generate_business_insight(
        category_counts={"Packaged Foods": 100, "Beverages": 42, "Personal Care": 20},
        sdi=0.74,
        sku_diversity_label="High",
        refill_signal="NORMAL",
        inventory_band="Medium",
        footfall_proxy=0.68,
        city_tier="TIER_2",
    )
    assert len(insight) > 20, f"Insight too short: '{insight}'"
    assert "shelf" in insight.lower(), f"Insight doesn't mention shelf: '{insight}'"
    assert "Packaged Foods" in insight, f"Insight doesn't mention top category"
    print(f"[PASS] Insight: {insight}")


def test_risk_flags_inventory_footfall():
    """High inventory + low footfall should trigger mismatch flag."""
    flags = compute_risk_flags(
        category_counts={"Packaged Foods": 200},
        sdi=0.80,
        inventory_value=90000,
        footfall_proxy=0.25,  # low footfall
    )
    assert "inventory_footfall_mismatch" in flags, f"Expected mismatch flag, got {flags}"
    print(f"[PASS] Risk flags: {flags}")


def test_risk_flags_concentration():
    """Single category dominance should trigger concentration flag."""
    flags = compute_risk_flags(
        category_counts={"Packaged Foods": 90, "Beverages": 5, "Other": 5},
        sdi=0.60,
        inventory_value=30000,
        footfall_proxy=0.50,
    )
    assert "single_category_concentration" in flags, f"Expected concentration flag, got {flags}"
    print(f"[PASS] Concentration risk: {flags}")


def test_risk_flags_clean():
    """Balanced store should have no flags."""
    flags = compute_risk_flags(
        category_counts={"Packaged Foods": 30, "Beverages": 25, "Personal Care": 20, "Dairy": 15},
        sdi=0.60,
        inventory_value=40000,
        footfall_proxy=0.60,
        regional_alignment_score=0.70,
        store_size_sqft=200,
    )
    assert len(flags) == 0, f"Expected no flags, got {flags}"
    print(f"[PASS] Clean store: no risk flags")


if __name__ == "__main__":
    test_coco_mapping_complete()
    test_zone_category_map_complete()
    test_classify_zone()
    test_sku_diversity_score_bounds()
    test_sku_diversity_monotonic()
    test_inventory_value_calculation()
    test_inventory_value_bands()
    test_refill_signal_high_sdi_uniform()
    test_refill_signal_high_sdi_variable()
    test_refill_signal_low_sdi()
    test_business_insight_generated()
    test_risk_flags_inventory_footfall()
    test_risk_flags_concentration()
    test_risk_flags_clean()
    print("\n=== ALL 14 TESTS PASSED ===")
