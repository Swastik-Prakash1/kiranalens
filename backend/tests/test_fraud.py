# backend/tests/test_fraud.py
"""Tests for Fraud Detection -- KiranaLens v3.0"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.hf_service import rule_based_fraud_prescreening


def test_staged_display_triggers():
    """Very high SDI + low stability + STAGED = STAGED_DISPLAY flag."""
    features = {
        "sdi": 0.92, "regional_alignment_score": 0.60,
        "stability_score": 0.40, "footfall_proxy_index": 0.50,
        "refill_signal": "STAGED", "possible_initial_stocking": False,
        "city_tier": "TIER_2", "store_size_proxy": "MEDIUM",
        "combined_multiplier": 1.2,
    }
    flags = rule_based_fraud_prescreening(features)
    flag_types = [f["flag_type"] for f in flags]
    assert "STAGED_DISPLAY" in flag_types, f"Expected STAGED_DISPLAY, got {flag_types}"
    print(f"[OK] Staged display detected: {flag_types}")


def test_inventory_demand_mismatch():
    """High SDI + low regional alignment = INVENTORY_DEMAND_MISMATCH."""
    features = {
        "sdi": 0.85, "regional_alignment_score": 0.20,
        "stability_score": 0.60, "footfall_proxy_index": 0.50,
        "refill_signal": "NORMAL", "possible_initial_stocking": False,
        "city_tier": "TIER_2", "store_size_proxy": "SMALL",
        "combined_multiplier": 1.0,
    }
    flags = rule_based_fraud_prescreening(features)
    flag_types = [f["flag_type"] for f in flags]
    assert "INVENTORY_DEMAND_MISMATCH" in flag_types
    print(f"[OK] Inventory-demand mismatch: {flag_types}")


def test_initial_stocking_fraud():
    """New store + very high SDI = INITIAL_STOCKING_FRAUD."""
    features = {
        "sdi": 0.90, "regional_alignment_score": 0.50,
        "stability_score": 0.50, "footfall_proxy_index": 0.60,
        "refill_signal": "RECENT_RESTOCK", "possible_initial_stocking": True,
        "city_tier": "TIER_1", "store_size_proxy": "SMALL",
        "combined_multiplier": 1.1,
    }
    flags = rule_based_fraud_prescreening(features)
    flag_types = [f["flag_type"] for f in flags]
    assert "INITIAL_STOCKING_FRAUD" in flag_types
    print(f"[OK] Initial stocking fraud: {flag_types}")


def test_clean_store_no_flags():
    """Normal store should produce no high-severity flags."""
    features = {
        "sdi": 0.65, "regional_alignment_score": 0.60,
        "stability_score": 0.70, "footfall_proxy_index": 0.65,
        "refill_signal": "NORMAL", "possible_initial_stocking": False,
        "city_tier": "TIER_2", "store_size_proxy": "MEDIUM",
        "combined_multiplier": 1.0,
    }
    flags = rule_based_fraud_prescreening(features)
    high_flags = [f for f in flags if f["severity"] == "HIGH"]
    assert len(high_flags) == 0, f"Expected no HIGH flags, got {high_flags}"
    print(f"[OK] Clean store: {len(flags)} flags (none HIGH)")


def test_location_mismatch():
    """TIER_4 + LARGE store = LOCATION_MISMATCH."""
    features = {
        "sdi": 0.70, "regional_alignment_score": 0.50,
        "stability_score": 0.60, "footfall_proxy_index": 0.30,
        "refill_signal": "NORMAL", "possible_initial_stocking": False,
        "city_tier": "TIER_4", "store_size_proxy": "LARGE",
        "combined_multiplier": 1.0,
    }
    flags = rule_based_fraud_prescreening(features)
    flag_types = [f["flag_type"] for f in flags]
    assert "LOCATION_MISMATCH" in flag_types
    print(f"[OK] Location mismatch: {flag_types}")
