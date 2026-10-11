import asyncio
from app.db import mongo
from app.services.places_client import search_places, PlacesLimitReached

async def main():
    await mongo.connect()
    try:
        raw, results, source = await search_places("cafe", 31.5204, 74.3587, 5)
        print("source:", source, "|", len(results), "places found")
        for r in results[:10]:
            print(r["distance_km"], "km |", r["name"], "|", r["rating"], "|", r["website"])
    except PlacesLimitReached as e:
        print(e)
    finally:
        await mongo.close()

asyncio.run(main())