"""P2 steps 2.1-2.2: rank nearby businesses and find their social pages."""
import asyncio
import math
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from app.db.mongo import get_db, oid
from app.models.schemas import Brand
from app.services.places_client import search_places

IG_RE = re.compile(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]{1,30})", re.I)
FB_RE = re.compile(r"https?://(?:www\.|m\.)?facebook\.com/([A-Za-z0-9.\-]{3,})", re.I)
IG_SKIP = {"p", "reel", "reels", "explore", "accounts", "stories", "tv", "about",
           "developer", "legal", "direct", "share", "sharer.php", "web"}
FB_SKIP = {"sharer", "sharer.php", "share", "dialog", "tr", "plugins", "policies", "help",
           "login", "groups", "events", "watch", "marketplace", "pages", "profile.php",
           "people", "hashtag", "photo", "photo.php", "permalink.php", "story.php"}


def _plain(s: str | None) -> str:
    """lowercase and strip accents: 'Café' -> 'cafe'"""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def find_social_links(text: str) -> dict:
    """First valid Instagram handle and Facebook page name found in text/HTML."""
    ig = next((m.group(1).rstrip(".") for m in IG_RE.finditer(text)
               if m.group(1).lower() not in IG_SKIP), None)
    fb = next((m.group(1).rstrip(".") for m in FB_RE.finditer(text)
               if m.group(1).lower() not in FB_SKIP), None)
    return {"instagram": ig, "facebook": fb}


def is_own_business(place: dict, brand_name: str, brand_website: str | None = None) -> bool:
    a, b = _plain(place.get("name")), _plain(brand_name)
    if a and b and (a == b or (len(b) >= 4 and (b in a or a in b))):
        return True
    if brand_website and place.get("website"):
        host = lambda u: urlparse(u if "//" in u else "//" + u).netloc.replace("www.", "").lower()
        return host(brand_website) == host(place["website"])
    return False


def score_place(p: dict, radius_km: float, industry: str) -> float:
    """Starting weights (my assumption, tune later): proximity 0.30, rating 0.25,
    review count 0.25, category match 0.20."""
    prox = max(0.0, 1 - (p.get("distance_km") or 0) / radius_km)
    rating = (p.get("rating") or 0) / 5
    reviews = min(math.log10(1 + (p.get("review_count") or 0)) / 3, 1.0)   # 1000 reviews = 1.0
    text = _plain(f'{p.get("category") or ""} {p.get("name") or ""}')
    cat = 1.0 if _plain(industry) in text else 0.0
    return round(0.30 * prox + 0.25 * rating + 0.25 * reviews + 0.20 * cat, 4)


async def _fetch_html(client: httpx.AsyncClient, url: str) -> str:
    try:
        r = await client.get(url, follow_redirects=True, timeout=10)
        if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
            return r.text
    except httpx.HTTPError:
        pass
    return ""


async def discover(places: list[dict], brand_name: str, industry: str, radius_km: float,
                   brand_website: str | None = None, limit: int = 15,
                   concurrency: int = 5) -> list[dict]:
    """Drop the brand itself, rank, keep top `limit`, then look for social links."""
    others = [p for p in places if not is_own_business(p, brand_name, brand_website)]
    for p in others:
        p["rank_score"] = score_place(p, radius_km, industry)
    top = sorted(others, key=lambda p: p["rank_score"], reverse=True)[:limit]

    sem = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": "ABGIE-FYP/1.0 (student project)"}
    async with httpx.AsyncClient(headers=headers) as client:
        async def one(p):
            site = p.get("website") or ""
            if not site:
                p["instagram"] = p["facebook"] = None
                return
            links = find_social_links(site)            # the website itself may be a social link
            if not (links["instagram"]):
                async with sem:
                    html = await _fetch_html(client, site)
                found = find_social_links(html)
                links = {"instagram": links["instagram"] or found["instagram"],
                         "facebook": links["facebook"] or found["facebook"]}
            p["instagram"], p["facebook"] = links["instagram"], links["facebook"]
        await asyncio.gather(*(one(p) for p in top))
    return top


async def save_competitors(brand_id: str, items: list[dict]) -> None:
    """Upsert by (brand_id, place_id). Never overwrites followers / engagement set later."""
    db = get_db()
    for p in items:
        fields = {"name": p["name"], "address": p.get("address"),
                  "distance_km": p.get("distance_km"), "category": p.get("category"),
                  "website": p.get("website"), "rating": p.get("rating"),
                  "review_count": p.get("review_count") or 0}
        set_doc = {k: v for k, v in fields.items() if v is not None}
        on_insert = {"followers_count": 0, "avg_engagement_rate": 0.0,
                     "created_at": datetime.now(timezone.utc)}
        if p.get("instagram"):
            set_doc["instagram_username"] = p["instagram"]
            set_doc["status"] = "discovered"
        else:
            on_insert["status"] = "no_public_instagram"
        await db.competitors.update_one(
            {"brand_id": brand_id, "place_id": p["place_id"]},
            {"$set": set_doc, "$setOnInsert": on_insert}, upsert=True)


async def run(brand_id: str) -> dict:
    db = get_db()
    doc = await db.brands.find_one({"_id": oid(brand_id)})
    if not doc:
        raise ValueError(f"brand {brand_id} not found")
    brand = Brand(**doc)
    _, places, source = await search_places(brand.industry, brand.lat, brand.lng, brand.radius_km)
    items = await discover(places, brand.name, brand.industry, brand.radius_km, brand.website)
    await save_competitors(brand_id, items)
    return {"places_source": source, "found": len(places), "kept": len(items),
            "with_instagram": sum(1 for p in items if p.get("instagram"))}