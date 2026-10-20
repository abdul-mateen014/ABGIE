import asyncio
from app.db import mongo
from app.services.places_client import search_places
from app.agents.competitor_discovery import discover

QUERY = "cafe"            # copy these 4 from your scripts/test_places.py
LAT, LNG = 31.5204, 74.3587
RADIUS_KM = 5
BRAND_NAME = "My Test Brand"   # a name that is NOT in the list

async def main():
    await mongo.connect()
    _, places, source = await search_places(QUERY, LAT, LNG, RADIUS_KM)
    print("places source:", source, "|", len(places), "found")
    top = await discover(places, BRAND_NAME, QUERY, RADIUS_KM)
    for p in top:
        print(f'{p["rank_score"]:.2f} | {p["distance_km"]} km | {p["name"]} | '
              f'site={bool(p.get("website"))} | ig={p["instagram"]} | fb={p["facebook"]}')
    print("\nwith website  :", sum(1 for p in top if p.get("website")), "/", len(top))
    print("with instagram:", sum(1 for p in top if p["instagram"]), "/", len(top))
    print("with facebook :", sum(1 for p in top if p["facebook"]), "/", len(top))
    await mongo.close()

asyncio.run(main())