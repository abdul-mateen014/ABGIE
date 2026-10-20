import pytest
from app.agents.competitor_discovery import find_social_links, is_own_business, score_place

def test_finds_instagram_in_html():
    html = '<a href="https://www.instagram.com/cafezouk/">IG</a>'
    assert find_social_links(html)["instagram"] == "cafezouk"

def test_ignores_post_links():
    html = '<a href="https://instagram.com/p/Cx12/">post</a> <a href="https://instagram.com/realcafe">x</a>'
    assert find_social_links(html)["instagram"] == "realcafe"

def test_facebook_page_and_skip_sharer():
    html = 'https://facebook.com/sharer/sharer.php?u=x https://www.facebook.com/FreddysCafeLahore'
    assert find_social_links(html)["facebook"] == "FreddysCafeLahore"

def test_nothing_found():
    assert find_social_links("<html>no links</html>") == {"instagram": None, "facebook": None}

def test_own_business_by_name_with_accent():
    assert is_own_business({"name": "Café Zouk"}, "cafe zouk")
    assert not is_own_business({"name": "Ben-T Cafe"}, "Cafe Zouk")

def test_own_business_by_website():
    assert is_own_business({"name": "X", "website": "https://www.mybrand.pk/menu"}, "Other", "http://mybrand.pk")

def test_closer_better_rated_place_scores_higher():
    near = {"distance_km": 0.3, "rating": 4.5, "review_count": 800, "category": "cafe", "name": "A"}
    far = {"distance_km": 4.0, "rating": 3.5, "review_count": 20, "category": "cafe", "name": "B"}
    assert score_place(near, 5, "cafe") > score_place(far, 5, "cafe")

def test_score_handles_missing_values():
    assert score_place({"distance_km": 1, "rating": None, "review_count": None}, 5, "cafe") >= 0