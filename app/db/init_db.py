import asyncio
from pymongo import AsyncMongoClient, ASCENDING, DESCENDING
from app.config import settings

COLLECTIONS = [
    "users", "brands", "social_accounts", "competitors", "competitor_posts",
    "intelligence_reports", "content_strategies", "decisions", "content_items",
    "queue_entries", "metrics", "strategy_weights", "adaptation_log", "explanations",
]

# (collection, keys, options)
INDEXES = [
    ("users", [("email", ASCENDING)], {"unique": True}),
    ("brands", [("user_id", ASCENDING)], {}),
    ("brands", [("user_id", ASCENDING), ("normalized_name", ASCENDING)],
         {"unique": True, "partialFilterExpression": {"normalized_name": {"$type": "string"}},
            "name": "unique_brand_name_per_user"}),
    ("social_accounts", [("brand_id", ASCENDING)], {}),
    ("competitors", [("brand_id", ASCENDING), ("place_id", ASCENDING)], {"unique": True}),
    ("competitor_posts", [("competitor_id", ASCENDING), ("posted_at", DESCENDING)], {}),
    ("competitor_posts", [("competitor_id", ASCENDING), ("external_id", ASCENDING)],
     {"unique": True, "partialFilterExpression": {"external_id": {"$type": "string"}}}),
    ("intelligence_reports", [("brand_id", ASCENDING), ("created_at", DESCENDING)], {}),
    ("content_strategies", [("brand_id", ASCENDING), ("status", ASCENDING)], {}),
    ("content_strategies", [("intelligence_id", ASCENDING)], {}),
    ("decisions", [("strategy_id", ASCENDING)], {}),
    ("content_items", [("strategy_id", ASCENDING), ("status", ASCENDING)], {}),
    ("queue_entries", [("content_id", ASCENDING)], {}),
    ("queue_entries", [("status", ASCENDING), ("scheduled_time", ASCENDING)], {}),
    ("metrics", [("queue_id", ASCENDING), ("collected_at", DESCENDING)], {}),
    ("strategy_weights", [("brand_id", ASCENDING)], {"unique": True}),
    ("adaptation_log", [("brand_id", ASCENDING), ("created_at", DESCENDING)], {}),
    ("explanations", [("brand_id", ASCENDING)], {}),
    ("explanations", [("decision_id", ASCENDING)], {}),
]

async def main():
    client = AsyncMongoClient(settings.mongodb_uri, tz_aware=True)
    db = client[settings.mongodb_db]
    existing = set(await db.list_collection_names())
    for name in COLLECTIONS:
        if name not in existing:
            await db.create_collection(name)
            print("created", name)
        else:
            print("exists ", name)
    for coll, keys, opts in INDEXES:
        idx = await db[coll].create_index(keys, **opts)
        print("index  ", coll, idx)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())