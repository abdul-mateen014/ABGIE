# Google Places API client
import hashlib
import math
from datetime import datetime, timezone

import httpx
from pymongo import ReturnDocument

from app.config import settings
from app.db.mongo import get_db

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.location", "places.rating", "places.userRatingCount",
    "places.websiteUri", "places.primaryType",
])


class PlacesLimitReached(Exception):
    pass


def haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _cache_key(query, lat, lng, radius_km):
    s = f"{query.strip().lower()}|{round(lat, 4)}|{round(lng, 4)}|{radius_km}"
    return hashlib.sha256(s.encode()).hexdigest()


async def _reserve_call(db):
    """Count one Google call for this month. Refuse if the limit is reached."""
    doc_id = "places_text_search:" + datetime.now(timezone.utc).strftime("%Y-%m")
    await db.api_usage.update_one({"_id": doc_id}, {"$setOnInsert": {"count": 0}}, upsert=True)
    res = await db.api_usage.find_one_and_update(
        {"_id": doc_id, "count": {"$lt": settings.places_monthly_limit}},
        {"$inc": {"count": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if res is None:
        raise PlacesLimitReached(
            f"Monthly Places limit ({settings.places_monthly_limit}) reached. No Google call made."
        )
    return res["count"]


def _parse(raw, lat, lng, radius_km):
    results = []
    for p in raw.get("places", []):
        loc = p.get("location", {})
        dist = haversine_km(lat, lng, loc.get("latitude", lat), loc.get("longitude", lng))
        if dist <= radius_km:  # locationBias is only a hint, so we enforce the radius
            results.append({
                "place_id": p.get("id"),
                "name": p.get("displayName", {}).get("text"),
                "address": p.get("formattedAddress"),
                "distance_km": round(dist, 2),
                "category": p.get("primaryType"),
                "rating": p.get("rating"),
                "review_count": p.get("userRatingCount"),
                "website": p.get("websiteUri"),
            })
    results.sort(key=lambda x: x["distance_km"])
    return results


async def search_places(query, lat, lng, radius_km, force_refresh=False):
    """Returns (raw_response, results, source) where source is 'cache' or 'google'."""
    db = get_db()
    key = _cache_key(query, lat, lng, radius_km)

    cached = await db.raw_api_responses.find_one({"_id": key})
    if cached and not force_refresh:
        raw = cached["response"]
        return raw, _parse(raw, lat, lng, radius_km), "cache"

    await _reserve_call(db)

    body = {
        "textQuery": query,
        "maxResultCount": 20,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": min(radius_km * 1000, 50000.0),
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_places_api_key,
        "X-Goog-FieldMask": FIELDS,
    }
    async with httpx.AsyncClient(timeout=20) as http:
        resp = await http.post(URL, json=body, headers=headers)
        resp.raise_for_status()
        raw = resp.json()

    await db.raw_api_responses.replace_one(
        {"_id": key},
        {"_id": key, "service": "places_text_search", "query": query,
         "lat": lat, "lng": lng, "radius_km": radius_km,
         "response": raw, "fetched_at": datetime.now(timezone.utc)},
        upsert=True,
    )
    return raw, _parse(raw, lat, lng, radius_km), "google"