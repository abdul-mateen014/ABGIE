import pytest
from bson import ObjectId
from pydantic import ValidationError
from app.models.schemas import Decision, Metric, BrandCreate, Brand, CompetitorPost

def test_decision_score():
    assert Decision.compute_score(0.7, 82, 5) == pytest.approx(52.4)

def test_engagement_rate():
    assert Metric.compute_engagement_rate(120, 14, 9, 22, 3400) == pytest.approx(4.85, abs=0.01)

def test_engagement_rate_zero_reach():
    assert Metric.compute_engagement_rate(10, 1, 1, 1, 0) == 0.0

def test_deviation():
    assert Metric.compute_deviation(4.1, 3.2) == pytest.approx(0.9)

FORM = dict(name="Cafe X", industry="cafe", target_audience="students",
            city="Lahore", lat=31.52, lng=74.35, radius_km=5)

def test_brand_form_ok():
    assert BrandCreate(**FORM).radius_km == 5

@pytest.mark.parametrize("r", [0, -1, 51])
def test_brand_radius_rejected(r):
    with pytest.raises(ValidationError):
        BrandCreate(**{**FORM, "radius_km": r})

def test_objectid_becomes_string():
    oid = ObjectId()
    b = Brand(_id=oid, user_id=oid, **FORM)
    assert b.id == str(oid) and b.user_id == str(oid)

def test_to_mongo_omits_id_and_none():
    d = Brand(user_id="u1", **FORM).to_mongo()
    assert "_id" not in d and "description" not in d

def test_post_needs_external_id():
    with pytest.raises(ValidationError):
        CompetitorPost(competitor_id="c1", posted_at="2026-10-01T10:00:00Z")