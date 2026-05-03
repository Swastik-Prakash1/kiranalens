# backend/app/services/hf_service.py
"""
KiranaLens v3.0 — HuggingFace Inference API Service.
Handles fraud analysis (Llama 3.2 Vision) and report generation (Llama 3.2).
Free tier, zero cost. Requires HF_TOKEN from env.
"""

import json
import logging
import os
import re
from dotenv import load_dotenv
from app.models.schemas import RiskFlag

load_dotenv()
logger = logging.getLogger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN", "")

# ============================================================================
# Fraud Analysis Prompts
# ============================================================================
FRAUD_SYSTEM_PROMPT = """You are a senior fraud analyst at an Indian NBFC reviewing a kirana store loan application.
You have been given structured features from computer vision analysis, geospatial data,
operational stability scoring, and regional demand alignment scoring.

Your job: identify cross-signal inconsistencies that indicate manipulation or misrepresentation.
Be a skeptical underwriter, not a lenient one.

You must respond ONLY with a valid JSON object. No prose, no markdown. Raw JSON only.

JSON schema:
{
  "manipulation_probability": <float 0.0-1.0>,
  "risk_flags": [
    {
      "flag_type": <one of: "INVENTORY_STUFFING", "SELECTIVE_PHOTOGRAPHY",
                   "LOCATION_MISMATCH", "CATEGORY_INFLATION", "ECONOMIC_IMPLAUSIBILITY",
                   "STAGED_DISPLAY", "INVENTORY_DEMAND_MISMATCH",
                   "GEO_DEMAND_INCONSISTENCY", "INITIAL_STOCKING_FRAUD">,
      "severity": <"HIGH" | "MEDIUM" | "LOW">,
      "confidence": <float 0.0-1.0>,
      "evidence": "<specific observation from the data>",
      "recommendation": <"REJECT" | "MANUAL_VERIFY" | "NOTE_FOR_RECORD">
    }
  ],
  "consistency_assessment": "<2-3 sentences>",
  "recommendation": <"APPROVE" | "VERIFY" | "REJECT">,
  "recommendation_rationale": "<1-2 sentences>"
}"""


def _build_fraud_prompt(features: dict) -> str:
    """Build the fraud analysis user prompt from pipeline features."""
    return f"""KIRANA STORE ASSESSMENT DATA:

VISION SIGNALS:
- Shelf Density Index (SDI): {features.get('sdi', 0)}
- SDI Confidence: {features.get('sdi_confidence', 0)}
- SDI Variance across images: {features.get('sdi_variance', 0)}
- SKU Diversity Count: {features.get('sku_diversity_count', 0)}
- Detected Categories: {features.get('detected_categories', [])}
- Inventory Density: {features.get('inventory_density_score', 0)}
- Refill Signal: {features.get('refill_signal', 'UNKNOWN')}
- Visual Organisation Score: {features.get('visual_organisation_score', 0)}
- Store Size: {features.get('store_size_proxy', 'UNKNOWN')}
- Total Products Detected: {features.get('total_products_detected', 0)}
- Image Quality: {features.get('overall_image_quality', 0)}

GEO SIGNALS:
- City Tier: {features.get('city_tier', 'TIER_3')}
- Road Type: {features.get('road_type', 'residential')}
- Competition within 300m: {features.get('competition_count_300m', 0)}
- Competition within 500m: {features.get('competition_count_500m', 0)}
- Footfall Proxy Index: {features.get('footfall_proxy_index', 0)}
- Amenity Score: {features.get('amenity_score', 0)}

ECONOMIC ESTIMATE:
- Daily Sales Mid: Rs.{features.get('daily_sales_mid', 0):,}
- Vision Multiplier: {features.get('vision_multiplier_applied', 0)}
- Geo Multiplier: {features.get('geo_multiplier_applied', 0)}
- Combined Multiplier: {features.get('combined_multiplier', 0)}

OPERATIONAL STABILITY SIGNALS:
- Stability Score: {features.get('stability_score', 0)} (0=unstable, 1=very stable)
- Stability Grade: {features.get('stability_grade', 'UNKNOWN')}
- Stability Factor Applied: {features.get('stability_factor', 1.0)}x
- Possible Initial Stocking Flag: {features.get('possible_initial_stocking', False)}
- Stability Explanation: {features.get('stability_explanation', 'N/A')}

REGIONAL DEMAND ALIGNMENT:
- India Region Detected: {features.get('india_region', 'UNKNOWN')}
- Alignment Score: {features.get('regional_alignment_score', 0)} (0=misaligned, 1=perfectly aligned)
- Alignment Grade: {features.get('alignment_grade', 'UNKNOWN')}
- Expected Regional Categories: {features.get('expected_categories', [])}
- Detected Matching: {features.get('detected_matching', [])}
- Missing Key Categories: {features.get('detected_missing', [])}
- Demand Mismatch Flag: {features.get('demand_mismatch', False)}

CROSS-SIGNAL CONSISTENCY CHECKS TO EVALUATE:
1. HIGH SDI ({features.get('sdi', 0)}) vs LOW footfall ({features.get('footfall_proxy_index', 0)}) -> flag INVENTORY_STUFFING
2. HIGH image quality variance -> flag SELECTIVE_PHOTOGRAPHY
3. TIER_3 location + LARGE store -> flag LOCATION_MISMATCH
4. HIGH SKU diversity + LOW image quality -> flag CATEGORY_INFLATION
5. Combined multiplier > 2.0 -> check ECONOMIC_IMPLAUSIBILITY
6. HIGH SDI + LOW stability ({features.get('stability_score', 0)}) -> flag STAGED_DISPLAY
7. HIGH SDI + LOW regional alignment ({features.get('regional_alignment_score', 0)}) -> flag INVENTORY_DEMAND_MISMATCH
8. HIGH alignment + LOW footfall -> flag GEO_DEMAND_INCONSISTENCY
9. possible_initial_stocking=True + SDI > 0.85 -> flag INITIAL_STOCKING_FRAUD

Analyse ALL signals. Report ALL inconsistencies you find. Be thorough."""


def _build_report_prompt(features: dict, estimate: dict, fraud: dict) -> str:
    """Build the human-readable report generation prompt."""
    return f"""Generate a concise professional credit assessment report for an Indian kirana store loan application.

KEY DATA:
- Location: {features.get('city_tier', 'N/A')}, {features.get('india_region', 'N/A').replace('_', ' ').title()}
- Store Size: {features.get('store_size_proxy', 'N/A')} (~{features.get('estimated_floor_area_sqft', 0)} sqft)
- SDI: {features.get('sdi', 0):.2f} | Products Detected: {features.get('total_products_detected', 0)}
- SKU Categories: {len(features.get('detected_categories', []))}

ECONOMIC ESTIMATE:
- Daily Revenue: Rs.{estimate.get('daily_sales_low', 0):,} - Rs.{estimate.get('daily_sales_high', 0):,} (mid: Rs.{estimate.get('daily_sales_mid', 0):,})
- Monthly Revenue: Rs.{estimate.get('monthly_revenue_low', 0):,} - Rs.{estimate.get('monthly_revenue_high', 0):,}
- Monthly Net Income: Rs.{estimate.get('monthly_income_low', 0):,} - Rs.{estimate.get('monthly_income_high', 0):,}
- Confidence: {estimate.get('confidence_score', 0):.0%}

STABILITY: {features.get('stability_grade', 'N/A')} (score: {features.get('stability_score', 0):.2f}, factor: {features.get('stability_factor', 1.0):.2f}x)
REGIONAL DEMAND: {features.get('alignment_grade', 'N/A')} alignment (score: {features.get('regional_alignment_score', 0):.2f})

RISK ASSESSMENT:
- Manipulation Probability: {fraud.get('manipulation_probability', 0):.0%}
- Risk Flags: {len(fraud.get('risk_flags', []))} identified
- Recommendation: {fraud.get('recommendation', 'N/A')}

Write a 200-word maximum professional credit assessment. Include:
1. Store profile summary (2 sentences)
2. Revenue assessment with confidence level
3. Key strengths
4. Risk factors (if any)
5. Final recommendation with rationale

Use professional financial language. No markdown formatting. Plain text only."""


def rule_based_fraud_prescreening(features: dict) -> list[dict]:
    """
    Fast, deterministic fraud flag generation that runs before the LLM call.
    These rules are economically grounded and cannot be gamed by LLM prompting.
    """
    flags = []

    sdi = features.get("sdi", 0.5)
    alignment = features.get("regional_alignment_score", 0.5)
    stability = features.get("stability_score", 0.5)
    footfall = features.get("footfall_proxy_index", 0.5)
    refill = features.get("refill_signal", "NORMAL")
    initial_flag = features.get("possible_initial_stocking", False)
    city_tier = features.get("city_tier", "TIER_3")
    store_size = features.get("store_size_proxy", "SMALL")
    combined_mult = features.get("combined_multiplier", 1.0)

    # Rule 1: High inventory + low regional alignment
    if sdi > 0.75 and alignment < 0.35:
        flags.append({
            "flag_type": "INVENTORY_DEMAND_MISMATCH",
            "severity": "MEDIUM",
            "confidence": 0.70,
            "evidence": f"SDI={sdi:.2f} (well-stocked) but regional alignment={alignment:.2f} (weak). Store stocks products inconsistent with local consumption patterns.",
            "recommendation": "MANUAL_VERIFY"
        })

    # Rule 2: Very high SDI + very low stability + STAGED signal
    if sdi > 0.88 and stability < 0.45 and refill == "STAGED":
        flags.append({
            "flag_type": "STAGED_DISPLAY",
            "severity": "HIGH",
            "confidence": 0.80,
            "evidence": f"SDI={sdi:.2f} (near-perfect) + stability_score={stability:.2f} (low) + refill=STAGED. All three signals agree: inventory appears artificially arranged.",
            "recommendation": "MANUAL_VERIFY"
        })

    # Rule 3: High alignment but low footfall
    if alignment > 0.70 and footfall < 0.30:
        flags.append({
            "flag_type": "GEO_DEMAND_INCONSISTENCY",
            "severity": "MEDIUM",
            "confidence": 0.65,
            "evidence": f"Regional demand alignment is high ({alignment:.2f}) but footfall proxy is low ({footfall:.2f}). Claimed demand pattern inconsistent with customer traffic.",
            "recommendation": "MANUAL_VERIFY"
        })

    # Rule 4: Initial stocking fraud
    if initial_flag and sdi > 0.85:
        flags.append({
            "flag_type": "INITIAL_STOCKING_FRAUD",
            "severity": "HIGH",
            "confidence": 0.75,
            "evidence": f"Store is <1 year old with SDI={sdi:.2f} -- very high inventory for a new store. Pattern matches initial bulk-stocking to inflate creditworthiness.",
            "recommendation": "MANUAL_VERIFY"
        })

    # Rule 5: Inventory stuffing -- high SDI + low footfall
    if sdi > 0.80 and footfall < 0.35:
        flags.append({
            "flag_type": "INVENTORY_STUFFING",
            "severity": "MEDIUM",
            "confidence": 0.65,
            "evidence": f"High shelf density ({sdi:.2f}) in a low-footfall area ({footfall:.2f}). Inventory may exceed what local traffic can sustain.",
            "recommendation": "NOTE_FOR_RECORD"
        })

    # Rule 6: Location mismatch
    if city_tier == "TIER_3" and store_size == "LARGE":
        flags.append({
            "flag_type": "LOCATION_MISMATCH",
            "severity": "MEDIUM",
            "confidence": 0.60,
            "evidence": f"LARGE store in TIER_3 location. Unusually large format for the area -- verify store legitimacy.",
            "recommendation": "MANUAL_VERIFY"
        })

    # Rule 7: Economic implausibility
    if combined_mult > 2.0:
        flags.append({
            "flag_type": "ECONOMIC_IMPLAUSIBILITY",
            "severity": "LOW",
            "confidence": 0.50,
            "evidence": f"Combined multiplier ({combined_mult:.2f}) exceeds 2.0x -- revenue estimate may be optimistic. Cross-verify with ground data.",
            "recommendation": "NOTE_FOR_RECORD"
        })

    return flags


async def analyze_fraud(features: dict) -> dict:
    """
    Run LLM-based fraud analysis via HuggingFace Inference API.
    Falls back to rule-based analysis if API unavailable.
    """
    if not HF_TOKEN or "your_token" in HF_TOKEN:
        logger.warning("No HF token -- using rule-based fraud analysis only")
        return _rule_only_fraud(features)

    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(
            model="meta-llama/Llama-3.2-11B-Vision-Instruct",
            token=HF_TOKEN,
        )

        prompt = _build_fraud_prompt(features)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": FRAUD_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        # Extract JSON from response (handle markdown fencing)
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
            result["llm_reasoning_available"] = True
            return result
        else:
            logger.warning("LLM response was not valid JSON, falling back")
            return _rule_only_fraud(features)

    except Exception as e:
        logger.error(f"HF fraud analysis failed: {e}")
        return _rule_only_fraud(features)


def _rule_only_fraud(features: dict) -> dict:
    """Fallback fraud analysis using only rule-based prescreening."""
    flags = rule_based_fraud_prescreening(features)

    if not flags:
        return {
            "manipulation_probability": 0.05,
            "risk_flags": [],
            "consistency_assessment": "No significant cross-signal inconsistencies detected. All visual and geospatial signals are mutually consistent.",
            "recommendation": "APPROVE",
            "recommendation_rationale": "Store signals are consistent and within expected ranges for the location and store profile.",
            "llm_reasoning_available": False,
        }

    high_flags = [f for f in flags if f["severity"] == "HIGH"]
    medium_flags = [f for f in flags if f["severity"] == "MEDIUM"]

    if high_flags:
        prob = min(0.80, 0.30 + len(high_flags) * 0.20 + len(medium_flags) * 0.10)
        rec = "REJECT" if len(high_flags) >= 2 else "VERIFY"
    elif medium_flags:
        prob = min(0.60, 0.15 + len(medium_flags) * 0.12)
        rec = "VERIFY"
    else:
        prob = min(0.30, len(flags) * 0.08)
        rec = "APPROVE"

    return {
        "manipulation_probability": round(prob, 2),
        "risk_flags": flags,
        "consistency_assessment": f"Rule-based analysis identified {len(flags)} potential concern(s). "
                                   f"{len(high_flags)} high severity, {len(medium_flags)} medium severity.",
        "recommendation": rec,
        "recommendation_rationale": f"Based on {len(flags)} detected risk signals requiring {'immediate review' if high_flags else 'verification'}.",
        "llm_reasoning_available": False,
    }


async def generate_report(features: dict, estimate: dict, fraud: dict) -> str:
    """
    Generate human-readable credit assessment report via LLM.
    Falls back to template-based report if API unavailable.
    """
    if not HF_TOKEN or "your_token" in HF_TOKEN:
        return _template_report(features, estimate, fraud)

    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(
            model="meta-llama/Llama-3.2-3B-Instruct",
            token=HF_TOKEN,
        )

        prompt = _build_report_prompt(features, estimate, fraud)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional credit analyst at an Indian NBFC. Write clear, data-driven assessments."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.3,
        )

        report = response.choices[0].message.content.strip()
        if len(report) > 50:
            return report
        return _template_report(features, estimate, fraud)

    except Exception as e:
        logger.error(f"HF report generation failed: {e}")
        return _template_report(features, estimate, fraud)


def _template_report(features: dict, estimate: dict, fraud: dict) -> str:
    """Template-based fallback report when LLM is unavailable."""
    city = features.get("city_tier", "N/A")
    region = features.get("india_region", "N/A").replace("_", " ").title()
    store_size = features.get("store_size_proxy", "N/A")
    sqft = features.get("estimated_floor_area_sqft", 0)
    sdi = features.get("sdi", 0)
    products = features.get("total_products_detected", 0)
    stability_grade = features.get("stability_grade", "N/A")
    alignment_grade = features.get("alignment_grade", "N/A")

    daily_low = estimate.get("daily_sales_low", 0)
    daily_mid = estimate.get("daily_sales_mid", 0)
    daily_high = estimate.get("daily_sales_high", 0)
    monthly_low = estimate.get("monthly_revenue_low", 0)
    monthly_high = estimate.get("monthly_revenue_high", 0)
    income_mid = estimate.get("monthly_income_mid", 0)
    confidence = estimate.get("confidence_score", 0)

    rec = fraud.get("recommendation", "VERIFY")
    risk_count = len(fraud.get("risk_flags", []))
    manip_prob = fraud.get("manipulation_probability", 0)

    return (
        f"CREDIT ASSESSMENT REPORT -- KiranaLens v3.0\n"
        f"{'='*50}\n\n"
        f"STORE PROFILE: {store_size} kirana store (~{sqft} sqft) in {city} zone, {region}. "
        f"Computer vision detected {products} products across shelf analysis with SDI of {sdi:.2f}.\n\n"
        f"REVENUE ESTIMATE: Daily revenue range Rs.{daily_low:,} - Rs.{daily_high:,} "
        f"(midpoint Rs.{daily_mid:,}/day). Monthly revenue Rs.{monthly_low:,} - Rs.{monthly_high:,}. "
        f"Estimated monthly net income: Rs.{income_mid:,}. Confidence: {confidence:.0%}.\n\n"
        f"OPERATIONAL INDICATORS: Stability grade is {stability_grade}. "
        f"Regional demand alignment is {alignment_grade}. "
        f"{'Store demonstrates mature, consistent operations.' if stability_grade == 'HIGH' else 'Operational consistency requires further verification.'}\n\n"
        f"RISK ASSESSMENT: Manipulation probability {manip_prob:.0%}. "
        f"{risk_count} risk flag(s) identified. "
        f"{'No significant concerns detected.' if risk_count == 0 else 'See detailed risk flags for specific concerns.'}\n\n"
        f"RECOMMENDATION: {rec}. "
        f"{'Store profile is consistent and creditworthy.' if rec == 'APPROVE' else 'Additional verification recommended before approval.' if rec == 'VERIFY' else 'Significant risk indicators present -- decline or require extensive verification.'}"
    )
