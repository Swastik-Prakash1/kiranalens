# backend/app/services/geo_service.py
"""
KiranaLens v3.0 — Geospatial Feature Extraction.
Uses OSMnx + Overpy (OpenStreetMap) for completely free geo intelligence.
Zero API keys required.

Extracts: city tier, road type, nearby amenities, competition density,
catchment density, footfall proxy, and india_region (v3.0).
"""

import logging
import time
import overpy
from geopy.geocoders import Nominatim
from app.models.schemas import GeoFeatures
from app.services.regional_demand_service import STATE_TO_REGION, _fallback_region

logger = logging.getLogger(__name__)

_geocoder = Nominatim(user_agent="kiranalens_geo_v3")
_overpass_api = overpy.Overpass()

# ============================================================================
# City Tier Classification
# Based on Indian government classification + population heuristics
# ============================================================================
TIER_1_CITIES = {
    "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "ahmedabad",
    "chennai", "kolkata", "pune", "jaipur", "lucknow", "kanpur",
    "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "patna",
    "vadodara", "ghaziabad", "ludhiana", "agra", "nashik", "faridabad",
    "meerut", "rajkot", "varanasi", "srinagar", "aurangabad",
    "dhanbad", "amritsar", "navi mumbai", "allahabad", "howrah",
    "ranchi", "gwalior", "jabalpur", "coimbatore", "vijayawada",
    "jodhpur", "madurai", "raipur", "kota", "chandigarh", "guwahati",
    "solapur", "hubli", "mysore", "mysuru", "tiruchirappalli",
    "bareilly", "aligarh", "tiruppur", "moradabad", "noida",
    "greater noida", "gurugram", "gurgaon", "new delhi",
}

TIER_2_CITIES = {
    "dehradun", "shimla", "jammu", "udaipur", "siliguri", "jamshedpur",
    "bokaro", "belgaum", "belagavi", "gulbarga", "kalaburagi",
    "mangalore", "mangaluru", "nellore", "kozhikode", "thrissur",
    "kollam", "tirunelveli", "salem", "erode", "vellore", "mathura",
    "firozabad", "bhilwara", "ajmer", "patiala", "karnal", "panipat",
    "rohtak", "hisar", "bhiwandi", "junagadh", "jamnagar", "bhavnagar",
    "gandhidham", "anand", "bilaspur", "korba", "rourkela", "sambalpur",
    "kakinada", "rajahmundry", "guntur", "warangal", "nizamabad",
    "karimnagar", "kharagpur", "durgapur", "asansol", "berhampore",
    "muzaffarpur", "gaya", "bhagalpur", "purnia", "dibrugarh",
    "jorhat", "tezpur", "imphal", "agartala", "shillong", "gangtok",
    "aizawl", "itanagar", "kohima", "pondicherry",
}


def _detect_city_tier(address: dict) -> str:
    """Detect city tier from geocoded address."""
    city_names = [
        (address.get("city") or "").lower().strip(),
        (address.get("town") or "").lower().strip(),
        (address.get("county") or "").lower().strip(),
        (address.get("suburb") or "").lower().strip(),
        (address.get("state_district") or "").lower().strip(),
    ]

    for name in city_names:
        if name in TIER_1_CITIES:
            return "TIER_1"
        if name in TIER_2_CITIES:
            return "TIER_2"

    return "TIER_3"  # default to TIER_3, NOT TIER_4


def _query_amenities(lat: float, lng: float, radius_m: int = 500) -> dict:
    """
    Query OpenStreetMap Overpass API for nearby amenities.
    Returns categorized counts of nearby POIs.
    """
    amenities = {
        "shops": 0,
        "restaurants": 0,
        "banks_atms": 0,
        "schools": 0,
        "hospitals": 0,
        "transit_stops": 0,
        "places_of_worship": 0,
        "fuel_stations": 0,
    }

    try:
        query = f"""
        [out:json][timeout:15];
        (
          node["amenity"](around:{radius_m},{lat},{lng});
          node["shop"](around:{radius_m},{lat},{lng});
        );
        out count;
        """
        result = _overpass_api.query(query)

        # Detailed query for categorization
        detail_query = f"""
        [out:json][timeout:15];
        (
          node["shop"](around:{radius_m},{lat},{lng});
          node["amenity"="restaurant"](around:{radius_m},{lat},{lng});
          node["amenity"="cafe"](around:{radius_m},{lat},{lng});
          node["amenity"="fast_food"](around:{radius_m},{lat},{lng});
          node["amenity"="bank"](around:{radius_m},{lat},{lng});
          node["amenity"="atm"](around:{radius_m},{lat},{lng});
          node["amenity"="school"](around:{radius_m},{lat},{lng});
          node["amenity"="hospital"](around:{radius_m},{lat},{lng});
          node["amenity"="clinic"](around:{radius_m},{lat},{lng});
          node["amenity"="bus_station"](around:{radius_m},{lat},{lng});
          node["highway"="bus_stop"](around:{radius_m},{lat},{lng});
          node["amenity"="place_of_worship"](around:{radius_m},{lat},{lng});
          node["amenity"="fuel"](around:{radius_m},{lat},{lng});
        );
        out body;
        """
        detail_result = _overpass_api.query(detail_query)

        for node in detail_result.nodes:
            tags = node.tags
            if "shop" in tags:
                amenities["shops"] += 1
            if tags.get("amenity") in ["restaurant", "cafe", "fast_food"]:
                amenities["restaurants"] += 1
            if tags.get("amenity") in ["bank", "atm"]:
                amenities["banks_atms"] += 1
            if tags.get("amenity") == "school":
                amenities["schools"] += 1
            if tags.get("amenity") in ["hospital", "clinic"]:
                amenities["hospitals"] += 1
            if tags.get("amenity") == "bus_station" or tags.get("highway") == "bus_stop":
                amenities["transit_stops"] += 1
            if tags.get("amenity") == "place_of_worship":
                amenities["places_of_worship"] += 1
            if tags.get("amenity") == "fuel":
                amenities["fuel_stations"] += 1

        logger.info(f"Amenities found within {radius_m}m: {amenities}")
        return amenities

    except Exception as e:
        logger.warning(f"Amenity query failed: {e}")
        return amenities


def _query_competition(lat: float, lng: float) -> tuple[int, int]:
    """
    Count competing shops (general stores, convenience stores, supermarkets)
    within 300m and 500m radius.
    """
    try:
        query = f"""
        [out:json][timeout:15];
        (
          node["shop"="convenience"](around:500,{lat},{lng});
          node["shop"="general"](around:500,{lat},{lng});
          node["shop"="supermarket"](around:500,{lat},{lng});
          node["shop"="grocery"](around:500,{lat},{lng});
          node["shop"="kiosk"](around:500,{lat},{lng});
        );
        out body;
        """
        result = _overpass_api.query(query)

        count_300m = 0
        count_500m = 0
        for node in result.nodes:
            from geopy.distance import geodesic
            dist = geodesic((lat, lng), (node.lat, node.lon)).meters
            count_500m += 1
            if dist <= 300:
                count_300m += 1

        return count_300m, count_500m

    except Exception as e:
        logger.warning(f"Competition query failed: {e}")
        return 0, 0


def _detect_road_type(lat: float, lng: float) -> tuple[str, float]:
    """
    Detect the type of road nearest to the GPS coordinates.
    Returns (road_type, road_type_score).
    """
    try:
        query = f"""
        [out:json][timeout:10];
        way["highway"](around:100,{lat},{lng});
        out body 1;
        """
        result = _overpass_api.query(query)

        if result.ways:
            highway_type = result.ways[0].tags.get("highway", "unclassified")
            road_map = {
                "motorway": ("HIGHWAY", 0.4),
                "trunk": ("TRUNK_ROAD", 0.5),
                "primary": ("PRIMARY_ROAD", 0.9),
                "secondary": ("SECONDARY_ROAD", 0.8),
                "tertiary": ("TERTIARY_ROAD", 0.7),
                "residential": ("RESIDENTIAL", 0.85),
                "living_street": ("RESIDENTIAL", 0.80),
                "service": ("SERVICE_ROAD", 0.5),
                "unclassified": ("UNCLASSIFIED", 0.6),
            }
            return road_map.get(highway_type, ("UNCLASSIFIED", 0.6))

        return ("UNCLASSIFIED", 0.5)

    except Exception as e:
        logger.warning(f"Road type query failed: {e}")
        return ("residential", 0.40)  # NEVER return "UNKNOWN" — always return a valid default


def _compute_footfall_proxy(
    amenity_score: float,
    road_score: float,
    competition_300m: int,
    city_tier: str,
) -> float:
    """
    Estimate footfall potential from amenity density, road type, and competition.
    Higher score = more potential customers passing by.
    """
    tier_weight = {"TIER_1": 0.90, "TIER_2": 0.75, "TIER_3": 0.55}
    tier_base = tier_weight.get(city_tier, 0.50)

    # Competition provides activity signal -- some competition = active market
    if competition_300m >= 5:
        comp_signal = 0.65  # very competitive area
    elif competition_300m >= 2:
        comp_signal = 0.85  # healthy market
    elif competition_300m == 1:
        comp_signal = 0.70  # some activity
    else:
        comp_signal = 0.40  # isolated

    raw = (
        tier_base * 0.30 +
        amenity_score * 0.25 +
        road_score * 0.20 +
        comp_signal * 0.25
    )
    return round(max(0.0, min(1.0, raw)), 3)


def get_geo_features(lat: float, lng: float) -> GeoFeatures:
    """
    Main entry point: extract all geospatial features for given GPS coordinates.
    Uses OSMnx + Overpy — completely free, zero API keys.
    """
    # GUARD: validate coordinates are actually in India
    # Common bug: test with 0,0 or non-India coordinates
    if not (6.0 <= lat <= 37.5 and 68.0 <= lng <= 97.5):
        print(f"[WARNING] GPS ({lat}, {lng}) is outside India bounds — using TIER_2 defaults")
        # Return a sensible default for demo/testing
        return GeoFeatures(
            lat=lat, lng=lng,
            city_tier="TIER_2",        # NOT TIER_4
            india_region="west_india",
            road_type="secondary",
            road_type_score=0.65,
            nearby_amenities={"schools":1,"healthcare":0,"transport":2,"offices":0,"competing_shops":5},
            amenity_score=0.45,
            competition_count_300m=2,
            competition_count_500m=5,
            competition_density_score=0.40,
            competition_adjustment=1.10,
            catchment_density_score=0.60,
            footfall_proxy_index=0.55,
            geo_multiplier=1.05,
            data_confidence=0.40,
            fallback_used=True,
        )

    fallback_used = False
    data_confidence = 0.8

    # --- Reverse geocode for city tier + state ---
    try:
        location = _geocoder.reverse(f"{lat},{lng}", timeout=10, language="en")
        if location:
            address = location.raw.get("address", {})
        else:
            address = {}
            fallback_used = True
            data_confidence -= 0.2
    except Exception as e:
        logger.warning(f"Geocoding failed: {e}")
        address = {}
        fallback_used = True
        data_confidence -= 0.3

    city_tier = _detect_city_tier(address)

    # --- India region (v3.0) ---
    state_raw = (address.get("state") or "").lower().strip()
    india_region = STATE_TO_REGION.get(state_raw) or _fallback_region(lat, lng)

    # --- Road type ---
    road_type, road_score = _detect_road_type(lat, lng)

    # --- Amenities ---
    amenities = _query_amenities(lat, lng, radius_m=500)
    total_amenities = sum(amenities.values())
    if total_amenities >= 20:
        amenity_score = 0.95
    elif total_amenities >= 10:
        amenity_score = 0.80
    elif total_amenities >= 5:
        amenity_score = 0.60
    elif total_amenities >= 1:
        amenity_score = 0.35
    else:
        amenity_score = 0.15
        fallback_used = True
        data_confidence -= 0.1

    # --- Competition ---
    comp_300, comp_500 = _query_competition(lat, lng)

    if comp_500 >= 10:
        comp_density = 0.95
        comp_adjustment = 0.75  # very saturated

    elif comp_500 >= 5:
        comp_density = 0.80
        comp_adjustment = 0.85

    elif comp_500 >= 2:
        comp_density = 0.50
        comp_adjustment = 1.00  # balanced market

    elif comp_500 == 1:
        comp_density = 0.30
        comp_adjustment = 1.05  # 🔥 reduced (was 1.10)

    elif comp_500 == 0:
        # ⚠️ DO NOT BOOST — could be API failure
        comp_density = 0.20
        comp_adjustment = 1.0   # 🔥 neutral

    else:
        comp_density = 0.10
        comp_adjustment = 1.0   # 🔥 safe fallback

    # 🔥 If geo data unreliable, do not boost
    if fallback_used:
        comp_adjustment = min(comp_adjustment, 1.0)

    # --- Catchment density ---
    catchment = round(min(1.0, (amenity_score * 0.5 + comp_density * 0.3 + road_score * 0.2)), 3)

    # --- Footfall proxy ---
    footfall = _compute_footfall_proxy(amenity_score, road_score, comp_300, city_tier)

    # --- Geo multiplier ---
    tier_mult = {"TIER_1": 1.40, "TIER_2": 1.15, "TIER_3": 0.90}
    tier_base = tier_mult.get(city_tier, 0.85)

    geo_raw = (
        tier_base * 0.40 +
        footfall * 0.30 +
        amenity_score * 0.15 +
        road_score * 0.15
    )
    geo_multiplier = round(max(0.7, min(1.3, geo_raw * 1.1)), 3)

    data_confidence = round(max(0.1, min(1.0, data_confidence)), 3)

    logger.info(f"Geo features: tier={city_tier}, region={india_region}, road={road_type}, "
                f"amenity_score={amenity_score}, footfall={footfall}, geo_mult={geo_multiplier}")

    return GeoFeatures(
        lat=lat,
        lng=lng,
        city_tier=city_tier,
        india_region=india_region,
        road_type=road_type,
        road_type_score=road_score,
        nearby_amenities=amenities,
        amenity_score=amenity_score,
        competition_count_300m=comp_300,
        competition_count_500m=comp_500,
        competition_density_score=comp_density,
        competition_adjustment=comp_adjustment,
        catchment_density_score=catchment,
        footfall_proxy_index=footfall,
        geo_multiplier=geo_multiplier,
        data_confidence=data_confidence,
        fallback_used=fallback_used,
    )
