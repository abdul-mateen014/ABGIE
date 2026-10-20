# Decision Layer Agent
"""P4 Decision Layer.

Score = (strategy weight x confidence) - risk penalty
Approve when score >= threshold.
Pure functions first (easy to test), run() connects them to MongoDB.
"""
from app.config import settings
from app.db.mongo import get_db, oid
from app.models.schemas import (
    ContentStrategy, Decision, IntelligenceReport, RiskFactor,
)

RISK_CAP = 10.0


def normalize(value: float, min_value: float, max_value: float, scale: float = 100.0) -> float:
    """Clamp value into [min_value, max_value] and map it to 0..scale."""
    if max_value <= min_value:
        raise ValueError("max_value must be greater than min_value")
    clipped = min(max(value, min_value), max_value)
    return (clipped - min_value) / (max_value - min_value) * scale


def combine_confidence(intelligence_conf: float, strategy_conf: float) -> float:
    """Average of the two agents' confidence, both on a 0-100 scale.
    (Assumption: simple average. Change here if the supervisor wants other weights.)"""
    return (normalize(intelligence_conf, 0, 100) + normalize(strategy_conf, 0, 100)) / 2


def calculate_risk_penalty(factors: list[RiskFactor],
                           factor_weights: dict[str, float] | None = None) -> float:
    """Sum of (factor weight x severity), kept between 0 and RISK_CAP."""
    fw = factor_weights or {}
    total = sum(fw.get(f.name, 1.0) * f.severity for f in factors)
    return min(total, RISK_CAP)


def decide(score: float, threshold: float) -> bool:
    """Approve when the score reaches the threshold (equal counts as approved)."""
    return score >= threshold


def retries_exhausted(retry_count: int, max_retries: int) -> bool:
    """retry_count = rejections so far BEFORE this attempt.
    True if this attempt was the last one allowed."""
    return retry_count + 1 >= max_retries


def evaluate(strategy_weight: float, intelligence_conf: float, strategy_conf: float,
             risk_factors: list[RiskFactor], threshold: float,
             factor_weights: dict[str, float] | None = None,
             strategy_id: str = "", retry_count: int = 0) -> Decision:
    """Pure decision logic. No database."""
    confidence = combine_confidence(intelligence_conf, strategy_conf)
    penalty = calculate_risk_penalty(risk_factors, factor_weights)
    score = round(Decision.compute_score(strategy_weight, confidence, penalty), 2)
    approved = decide(score, threshold)
    if approved:
        reason = f"Score {score:.2f} is at or above the threshold {threshold:g}."
    else:
        reason = f"Score {score:.2f} is below the threshold {threshold:g} (risk penalty {penalty:g})."
    return Decision(
        strategy_id=strategy_id, strategy_weight=strategy_weight,
        confidence=round(confidence, 2), risk_factors=risk_factors,
        risk_penalty=penalty, score=score, threshold=threshold,
        approved=approved, reason=reason, retry_count=retry_count,
    )


async def run(strategy_id: str, retry_count: int = 0) -> dict:
    """Read the strategy + its intelligence report, decide, save the decision,
    update the strategy status."""
    db = get_db()

    strat_doc = await db.content_strategies.find_one({"_id": oid(strategy_id)})
    if not strat_doc:
        raise ValueError(f"strategy {strategy_id} not found")
    strategy = ContentStrategy(**strat_doc)

    report_doc = await db.intelligence_reports.find_one({"_id": oid(strategy.intelligence_id)})
    if not report_doc:
        raise ValueError(f"intelligence report {strategy.intelligence_id} not found")
    report = IntelligenceReport(**report_doc)

    # risk factors come from the BI agent's report (empty list = no penalty)
    factors = [RiskFactor(**f) for f in report.strategy_object.get("risk_factors", [])]

    # per-brand threshold if the adaptive agent has set one, else the config default
    weights_doc = await db.strategy_weights.find_one({"brand_id": strategy.brand_id}) or {}
    threshold = weights_doc.get("thresholds", {}).get("approval", settings.approval_threshold)

    decision = evaluate(
        strategy_weight=strategy.strategy_weight,
        intelligence_conf=report.confidence,
        strategy_conf=strategy.confidence,
        risk_factors=factors, threshold=threshold,
        factor_weights=None,   # per-risk-factor weights are not stored yet; default 1.0 each
        strategy_id=strategy_id, retry_count=retry_count,
    )

    exhausted = (not decision.approved) and retries_exhausted(retry_count, settings.max_retries)
    if exhausted:
        decision.reason += " Maximum retries reached; needs user review."

    saved = await db.decisions.insert_one(decision.to_mongo())
    await db.content_strategies.update_one(
        {"_id": strat_doc["_id"]},
        {"$set": {"status": "approved" if decision.approved else "rejected"}},
    )
    return {
        "decision_id": str(saved.inserted_id),
        "approved": decision.approved,
        "score": decision.score,
        "reason": decision.reason,
        "retry_count": retry_count,
        "needs_user_review": exhausted,
    }