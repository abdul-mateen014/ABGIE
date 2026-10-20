import pytest
from app.agents.decision_layer import (
    normalize, combine_confidence, calculate_risk_penalty,
    decide, retries_exhausted, evaluate,
)
from app.models.schemas import RiskFactor


def rf(name, sev):
    return RiskFactor(name=name, severity=sev)


# ---- normalize
def test_normalize_middle():
    assert normalize(5, 0, 10) == pytest.approx(50)


def test_normalize_clamps():
    assert normalize(12, 0, 10) == 100
    assert normalize(-3, 0, 10) == 0


def test_normalize_bad_range():
    with pytest.raises(ValueError):
        normalize(1, 5, 5)


# ---- confidence: (80 + 60) / 2 = 70
def test_combine_confidence():
    assert combine_confidence(80, 60) == pytest.approx(70)


# ---- risk penalty
def test_penalty_sum():  # 3 + 2 = 5
    assert calculate_risk_penalty([rf("competitor_activity", 3), rf("market_volatility", 2)]) == 5


def test_penalty_empty():
    assert calculate_risk_penalty([]) == 0


def test_penalty_capped():  # 5 + 5 + 5 = 15 -> capped at 10
    assert calculate_risk_penalty([rf("a", 5), rf("b", 5), rf("c", 5)]) == 10


def test_penalty_with_factor_weight():  # 0.5 x 4 + 1.0 x 2 = 4
    assert calculate_risk_penalty([rf("a", 4), rf("b", 2)], {"a": 0.5}) == pytest.approx(4)


# ---- decide
def test_decide_above_below_equal():
    assert decide(52.4, 50) is True
    assert decide(49.9, 50) is False
    assert decide(50, 50) is True


# ---- retries: max 3 attempts
def test_retries_exhausted():
    assert retries_exhausted(0, 3) is False
    assert retries_exhausted(1, 3) is False
    assert retries_exhausted(2, 3) is True


# ---- full decision
# weight 0.7, confidence (80+84)/2 = 82, penalty 3+2 = 5  ->  0.7 x 82 - 5 = 52.4
def test_evaluate_approved():
    d = evaluate(0.7, 80, 84, [rf("competitor_activity", 3), rf("market_volatility", 2)], 50)
    assert d.confidence == pytest.approx(82)
    assert d.risk_penalty == 5
    assert d.score == pytest.approx(52.4)
    assert d.approved is True


# weight 0.5, confidence 60, penalty 5+5 = 10  ->  0.5 x 60 - 10 = 20  -> rejected
def test_evaluate_rejected_high_risk():
    d = evaluate(0.5, 60, 60, [rf("a", 5), rf("b", 5)], 50)
    assert d.score == pytest.approx(20)
    assert d.approved is False
    assert "below" in d.reason


# exactly at the threshold: weight 1.0, confidence 55, no risk -> 55 vs 55 -> approved
def test_evaluate_exact_threshold():
    d = evaluate(1.0, 55, 55, [], 55)
    assert d.score == pytest.approx(55)
    assert d.approved is True