# backend/app/services/stability_service.py
"""
KiranaLens v3.0 — Operational Stability Signal.
Pure Python, zero-dependency. Synthesises visual evidence about whether a store
reflects genuine, stable demand or temporary/artificial stocking.

Economic rationale:
- A mature, consistently-operating store shows natural shelf gaps (products sold)
- Refill patterns indicate products are MOVING (demand), not just stored
- High SDI consistency across images indicates a real store, not selective photography
- Very uniform + very full shelves + young store = suspicious (possible staged inventory)
"""

import logging
from app.models.schemas import OperationalStabilityResult

logger = logging.getLogger(__name__)


def compute_operational_stability(
    sdi: float,
    sdi_variance: float,
    refill_signal: str,
    visual_organisation_score: float,
    inventory_density_score: float,
    years_in_operation: int = 0,
) -> OperationalStabilityResult:
    """
    Estimate operational stability of a kirana store from visual and optional metadata signals.

    Returns stability_score [0,1] and stability_factor [0.85, 1.15] for economic formula.
    """

    signals = {}  # transparency dict

    # -- Signal 1: SDI Level Score --
    # Well-stocked (0.5-0.85) = healthy. Too empty or suspiciously full = lower score.
    if 0.50 <= sdi <= 0.85:
        sdi_score = 0.85 + ((sdi - 0.50) / 0.35) * 0.15  # peaks at 1.0 around SDI=0.85
    elif sdi > 0.85:
        sdi_score = 1.0 - ((sdi - 0.85) / 0.15) * 0.25   # drops slightly for very full shelves
    else:  # sdi < 0.50
        sdi_score = sdi / 0.50 * 0.70                      # scales up to 0.70 at SDI=0.50
    sdi_score = max(0.0, min(1.0, sdi_score))
    signals["sdi_level_score"] = round(sdi_score, 3)

    # -- Signal 2: Consistency Score (SDI Variance) --
    # Low variance = consistent stocking across images = real store
    # High variance = selective photography or inconsistent conditions
    if sdi_variance < 0.02:
        # Near-zero variance: could be staged OR genuinely consistent
        if sdi > 0.88:
            consistency_score = 0.55  # suspiciously perfect -- staged flag territory
        else:
            consistency_score = 0.85  # consistently normal -- genuine
    elif sdi_variance <= 0.08:
        consistency_score = 0.90  # natural small variation -- best signal
    elif sdi_variance <= 0.15:
        consistency_score = 0.70  # moderate variation -- acceptable
    elif sdi_variance <= 0.25:
        consistency_score = 0.50  # high variation -- selective photography concern
    else:
        consistency_score = 0.30  # very high variance -- strong inconsistency flag
    signals["consistency_score"] = round(consistency_score, 3)

    # -- Signal 3: Refill Pattern Score --
    refill_scores = {
        "RECENT_RESTOCK": 0.85,  # products are moving -- demand is real
        "NORMAL": 1.00,          # natural gaps -- best stability signal
        "LOW_STOCK": 0.55,       # possible demand weakness or cash constraint
        "STAGED": 0.30,          # high suspicion of artificial inventory
    }
    refill_score = refill_scores.get(refill_signal, 0.65)
    signals["refill_score"] = round(refill_score, 3)

    # -- Signal 4: Visual Organisation Score --
    # Moderate organisation = real store. Too perfect = staged.
    if visual_organisation_score > 0.90:
        org_score = 0.60  # suspiciously perfect arrangement
    elif visual_organisation_score >= 0.60:
        org_score = 0.90  # well-organised but natural
    elif visual_organisation_score >= 0.35:
        org_score = 0.75  # moderately organised -- typical kirana
    else:
        org_score = 0.50  # very disorganised -- possible new or struggling store
    signals["organisation_score"] = round(org_score, 3)

    # -- Signal 5: Years in Operation Adjustment --
    years_bonus = 0.0
    years_flag = False
    if years_in_operation > 0:
        if years_in_operation >= 5:
            years_bonus = 0.10  # strong maturity signal
            if refill_signal in ["RECENT_RESTOCK", "NORMAL"]:
                years_bonus = 0.15  # best possible: old store with active turnover
        elif years_in_operation >= 2:
            years_bonus = 0.05  # modest maturity
        elif years_in_operation == 1:
            years_bonus = 0.00  # neutral
        else:  # < 1 year (shouldn't happen with int, but defensive)
            years_bonus = -0.05
            if sdi > 0.85:
                years_flag = True  # new store + very full = initial stocking flag
        signals["years_bonus"] = round(years_bonus, 3)
        signals["years_provided"] = True
    else:
        signals["years_bonus"] = 0.0
        signals["years_provided"] = False

    # -- Aggregate Stability Score --
    raw_score = (
        sdi_score           * 0.25 +
        consistency_score   * 0.30 +
        refill_score        * 0.25 +
        org_score           * 0.20
    ) + years_bonus

    stability_score = round(max(0.0, min(1.0, raw_score)), 3)

    # -- Map to Stability Factor [0.85, 1.15] --
    # stability_score=0.0 -> factor=0.85, score=0.5 -> factor=1.0, score=1.0 -> factor=1.15
    stability_factor = round(0.85 + (stability_score * 0.30), 3)
    stability_factor = max(0.85, min(1.15, stability_factor))

    # -- Grade --
    if stability_score >= 0.72:
        grade = "HIGH"
    elif stability_score >= 0.48:
        grade = "MEDIUM"
    else:
        grade = "LOW"

    # -- Human-readable explanation --
    explanation_parts = []

    if refill_signal == "NORMAL":
        explanation_parts.append("Natural shelf gaps indicate products are actively selling.")
    elif refill_signal == "RECENT_RESTOCK":
        explanation_parts.append("Recent restocking detected -- goods are moving, demand is active.")
    elif refill_signal == "STAGED":
        explanation_parts.append("Shelf arrangement appears artificially uniform -- possible staged inventory.")
    elif refill_signal == "LOW_STOCK":
        explanation_parts.append("Low stock levels suggest either demand weakness or cash flow constraint.")

    if sdi_variance <= 0.08 and sdi > 0.88:
        explanation_parts.append("Near-perfect shelf uniformity across images raises staging concern.")
    elif consistency_score >= 0.85:
        explanation_parts.append("Inventory levels are consistent across all submitted images.")
    else:
        explanation_parts.append("Significant variation in shelf density across images -- possible selective photography.")

    if years_in_operation >= 5:
        explanation_parts.append(f"Store reports {years_in_operation} years of operation -- strong maturity signal.")
    elif years_flag:
        explanation_parts.append("New store (<1 year) with very full shelves -- possible initial stocking, not sustained demand.")

    explanation_parts.append(f"Overall stability grade: {grade} (score: {stability_score:.2f}). Formula factor: {stability_factor:.2f}x.")

    explanation = " ".join(explanation_parts)

    logger.info(f"Stability: score={stability_score}, grade={grade}, factor={stability_factor}, initial_stocking_flag={years_flag}")

    return OperationalStabilityResult(
        stability_score=stability_score,
        stability_factor=stability_factor,
        stability_grade=grade,
        possible_initial_stocking=years_flag,
        stability_explanation=explanation,
        signals_used=signals,
    )
