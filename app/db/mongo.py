from bson import ObjectId
from pymongo import AsyncMongoClient
from app.config import settings

client: AsyncMongoClient | None = None


async def connect():
    global client
    # tz_aware=True: datetimes come back timezone-aware, matching utcnow()
    client = AsyncMongoClient(settings.mongodb_uri, tz_aware=True)
    await client.admin.command("ping")   # fails here if the connection is wrong


async def close():
    if client:
        await client.close()


def get_db():
    return client[settings.mongodb_db]


def oid(value: str) -> ObjectId:
    """Use ONLY when querying a document's own _id.
    Reference fields (brand_id, strategy_id ...) are always stored and queried as plain strings."""
    return ObjectId(value)