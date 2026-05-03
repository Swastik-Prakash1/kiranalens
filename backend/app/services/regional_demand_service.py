# backend/app/services/regional_demand_service.py
"""
KiranaLens v3.0 — Regional Demand Alignment Signal.
Pure Python lookup + matching signal. No ML, no API.
Answers: "Is this store stocking what people in this region actually buy?"

Economic rationale:
A store stocking region-appropriate products will have higher turnover
because products match local demand. Misaligned stores face slower
inventory movement and weaker revenue predictability.

Regional FMCG demand profiles are informed by NielsenIQ India data.
"""

import logging
from geopy.geocoders import Nominatim
from app.models.schemas import RegionalDemandResult

logger = logging.getLogger(__name__)

# ============================================================================
# GPS -> India Region Mapping
# Based on standard Indian census regional groupings
# ============================================================================
STATE_TO_REGION = {
    # North India
    "uttar pradesh": "north_india", "haryana": "north_india",
    "punjab": "north_india", "rajasthan": "north_india",
    "himachal pradesh": "north_india", "uttarakhand": "north_india",
    "jammu and kashmir": "north_india", "ladakh": "north_india",
    "chandigarh": "north_india", "delhi": "north_india",

    # South India
    "tamil nadu": "south_india", "kerala": "south_india",
    "karnataka": "south_india", "andhra pradesh": "south_india",
    "telangana": "south_india", "puducherry": "south_india",
    "lakshadweep": "south_india",

    # East India
    "west bengal": "east_india", "odisha": "east_india",
    "bihar": "east_india", "jharkhand": "east_india",
    "assam": "east_india", "sikkim": "east_india",
    "meghalaya": "east_india", "manipur": "east_india",
    "mizoram": "east_india", "nagaland": "east_india",
    "arunachal pradesh": "east_india", "tripura": "east_india",

    # West India
    "maharashtra": "west_india", "gujarat": "west_india",
    "goa": "west_india", "dadra and nagar haveli": "west_india",
    "daman and diu": "west_india",

    # Central India
    "madhya pradesh": "central_india", "chhattisgarh": "central_india",
}

# ============================================================================
# Regional FMCG Demand Profiles (NielsenIQ-informed)
# ============================================================================
REGIONAL_DEMAND = {
    "north_india": {
        "primary":   ["atta_wheat_flour", "biscuits", "dairy_products", "snacks_namkeen",
                      "packaged_spices", "edible_oils_mustard", "beverages_tea"],
        "secondary": ["personal_care_soaps", "household_care", "baby_care",
                      "instant_noodles", "packaged_food"],
        "weight":    {"primary": 0.70, "secondary": 0.30}
    },
    "south_india": {
        "primary":   ["rice_products", "coconut_oil", "packaged_spices", "beverages_coffee",
                      "idli_dosa_mixes", "pickles_condiments", "personal_care_hair_oil"],
        "secondary": ["biscuits", "snacks", "beverages_cold", "edible_oils_sunflower",
                      "packaged_food"],
        "weight":    {"primary": 0.65, "secondary": 0.35}
    },
    "east_india": {
        "primary":   ["rice_products", "mustard_oil", "beverages_tea", "fish_products_canned",
                      "packaged_spices", "biscuits", "dairy_products"],
        "secondary": ["snacks", "personal_care_soaps", "household_care",
                      "packaged_food", "beverages_cold"],
        "weight":    {"primary": 0.65, "secondary": 0.35}
    },
    "west_india": {
        "primary":   ["snacks_namkeen", "beverages_cold", "packaged_food", "biscuits",
                      "edible_oils_groundnut", "beverages_tea", "dairy_products"],
        "secondary": ["personal_care", "household_care", "packaged_spices",
                      "instant_noodles", "atta_wheat_flour"],
        "weight":    {"primary": 0.70, "secondary": 0.30}
    },
    "central_india": {
        "primary":   ["atta_wheat_flour", "edible_oils", "biscuits", "snacks_namkeen",
                      "packaged_spices", "beverages_tea", "dairy_products"],
        "secondary": ["personal_care", "household_care", "packaged_food",
                      "instant_noodles", "beverages_cold"],
        "weight":    {"primary": 0.65, "secondary": 0.35}
    },
}

# ============================================================================
# Vision -> Regional Category Mapping
# Maps detected_categories (from VisionService) to regional FMCG categories
# ============================================================================
VISION_TO_REGIONAL_MAP = {
    "beverages_bottles":     ["beverages_cold", "beverages_tea", "beverages_coffee"],
    "packaged_snacks":       ["snacks_namkeen", "biscuits", "packaged_food"],
    "canned_boxed_goods":    ["packaged_food", "dairy_products", "fish_products_canned"],
    "bulk_staples":          ["atta_wheat_flour", "rice_products"],
    "tall_narrow_items":     ["edible_oils_mustard", "edible_oils_sunflower",
                              "edible_oils_groundnut", "coconut_oil", "edible_oils",
                              "mustard_oil"],
    "personal_care_items":   ["personal_care_soaps", "personal_care_hair_oil", "personal_care"],
    "household_items":       ["household_care"],
    "premium_brands":        ["beverages_cold", "packaged_food", "snacks_namkeen"],
    "health_wellness":       ["baby_care", "personal_care"],
    "general_fmcg":          ["biscuits", "packaged_food", "snacks_namkeen"],
    "beverages_cold_zone":   ["beverages_cold"],
    "dairy_refrigerated":    ["dairy_products"],
    "spices_condiments":     ["packaged_spices", "pickles_condiments"],
    "instant_foods":         ["instant_noodles", "idli_dosa_mixes"],
}

_geocoder = Nominatim(user_agent="kiranalens_regional_v1")


def _gps_to_region(lat: float, lng: float) -> str:
    """Map GPS coordinates to India region via reverse geocoding."""
    try:
        location = _geocoder.reverse(f"{lat},{lng}", timeout=10, language="en")
        if not location:
            return _fallback_region(lat, lng)
        address = location.raw.get("address", {})
        state = (address.get("state") or "").lower().strip()
        region = STATE_TO_REGION.get(state)
        if region:
            logger.info(f"Region detected: {state} -> {region}")
            return region
        return _fallback_region(lat, lng)
    except Exception as e:
        logger.warning(f"Region geocoding failed: {e}")
        return _fallback_region(lat, lng)


def _fallback_region(lat: float, lng: float) -> str:
    """
    Fallback GPS bounding box region detection when geocoding fails.
    Uses approximate regional bounding boxes for India.
    """
    if lat > 28.0 and lng < 80.0:
        return "north_india"
    elif lat < 15.0:
        return "south_india"
    elif lng > 85.0 and lat < 25.0:
        return "east_india"
    elif lng < 75.0 and lat < 25.0:
        return "west_india"
    else:
        return "central_india"


def _expand_detected_to_regional(detected_categories: list[str]) -> set[str]:
    """
    Map vision-detected categories to regional FMCG category names.
    A single vision category can match multiple regional categories.
    """
    regional_cats: set[str] = set()
    for vis_cat in detected_categories:
        mapped = VISION_TO_REGIONAL_MAP.get(vis_cat, [])
        regional_cats.update(mapped)
    return regional_cats


def compute_regional_demand_alignment(
    lat: float,
    lng: float,
    detected_categories: list[str],
    india_region: str = "",
) -> RegionalDemandResult:
    """
    Compute alignment between a store's detected inventory and the
    expected regional FMCG consumption pattern.

    Parameters:
      lat, lng: GPS coordinates
      detected_categories: list from VisionService (e.g. ["beverages_bottles", "packaged_snacks"])
      india_region: pre-computed from GeoService if available (avoids re-geocoding)
    """

    # Use pre-computed region or geocode fresh
    region = india_region if india_region else _gps_to_region(lat, lng)
    if region not in REGIONAL_DEMAND:
        region = "central_india"  # safe default

    demand_profile = REGIONAL_DEMAND[region]
    expected_primary = set(demand_profile["primary"])
    expected_secondary = set(demand_profile["secondary"])
    all_expected = expected_primary | expected_secondary

    # Expand vision categories to regional category names
    detected_regional = _expand_detected_to_regional(detected_categories)

    # Count matches -- weighted: primary matches count more
    primary_matches = detected_regional & expected_primary
    secondary_matches = detected_regional & expected_secondary
    all_matches = primary_matches | secondary_matches

    # Weighted alignment score
    weights = demand_profile["weight"]
    primary_score = len(primary_matches) / max(len(expected_primary), 1)
    secondary_score = len(secondary_matches) / max(len(expected_secondary), 1)

    raw_alignment = (
        primary_score * weights["primary"] +
        secondary_score * weights["secondary"]
    )
    alignment_score = round(max(0.0, min(1.0, raw_alignment)), 3)

    # Determine grade
    if alignment_score >= 0.70:
        grade = "STRONG"
        demand_mismatch = False
    elif alignment_score >= 0.40:
        grade = "MODERATE"
        demand_mismatch = False
    else:
        grade = "WEAK"
        demand_mismatch = True

    # Map to demand alignment factor [0.90, 1.10]
    # score=0 -> 0.90, score=0.5 -> 1.00, score=1.0 -> 1.10
    demand_factor = round(0.90 + (alignment_score * 0.20), 3)
    demand_factor = max(0.90, min(1.10, demand_factor))

    # What's missing and what matched
    detected_matching = sorted(list(all_matches))
    detected_missing = sorted(list(all_expected - detected_regional))

    # Explanation
    region_display = region.replace("_", " ").title()
    if grade == "STRONG":
        primary_examples = ", ".join(sorted(primary_matches)[:3]) if primary_matches else "none"
        explanation = (
            f"Store inventory strongly aligns with {region_display} demand patterns. "
            f"{len(primary_matches)} of {len(expected_primary)} primary regional categories detected "
            f"({primary_examples}). "
            f"High turnover probability for regionally-demanded products. Factor: +{demand_factor:.2f}x."
        )
    elif grade == "MODERATE":
        missing_examples = ", ".join(sorted(all_expected - detected_regional)[:3])
        explanation = (
            f"Store inventory moderately aligns with {region_display} demand patterns. "
            f"{len(all_matches)} of {len(all_expected)} expected categories detected. "
            f"Missing key categories: {missing_examples}. "
            f"Moderate demand predictability. Factor: {demand_factor:.2f}x."
        )
    else:
        primary_examples = ", ".join(sorted(expected_primary)[:4])
        explanation = (
            f"Store inventory shows weak alignment with {region_display} demand. "
            f"Only {len(all_matches)} of {len(all_expected)} expected categories detected. "
            f"A {region_display} store typically stocks: {primary_examples}. "
            f"Possible demand mismatch -- lower turnover likely. Factor: {demand_factor:.2f}x."
        )

    logger.info(f"Regional alignment: region={region}, score={alignment_score}, grade={grade}, factor={demand_factor}")

    return RegionalDemandResult(
        india_region=region,
        regional_alignment_score=alignment_score,
        demand_alignment_factor=demand_factor,
        alignment_grade=grade,
        expected_categories=sorted(list(all_expected)),
        detected_matching=detected_matching,
        detected_missing=detected_missing,
        demand_mismatch=demand_mismatch,
        alignment_explanation=explanation,
    )
