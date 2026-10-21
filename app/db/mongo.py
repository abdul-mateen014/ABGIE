from bson import ObjectId
from pymongo import ASCENDING, AsyncMongoClient
from app.config import settings

client: AsyncMongoClient | None = None


try:
    import certifi
    ca_file = certifi.where()
except Exception:
    ca_file = None


async def connect():
    global client
    # tz_aware=True: datetimes come back timezone-aware, matching utcnow()
    kwargs = {"tz_aware": True, "serverSelectionTimeoutMS": 10000}
    if ca_file:
        kwargs["tlsCAFile"] = ca_file

    client = AsyncMongoClient(settings.mongodb_uri, **kwargs)
    await client.admin.command("ping")   # fails here if the connection is wrong
    await client[settings.mongodb_db].brands.create_index(
        [("user_id", ASCENDING), ("normalized_name", ASCENDING)],
        unique=True,
        partialFilterExpression={"normalized_name": {"$type": "string"}},
        name="unique_brand_name_per_user",
    )



async def close():
    if client:
        await client.close()


def get_db():
    return client[settings.mongodb_db]


def oid(value: str) -> ObjectId:
    """Use ONLY when querying a document's own _id.
    Reference fields (brand_id, strategy_id ...) are always stored and queried as plain strings."""
    return ObjectId(value)


if __name__ == "__main__":
    import asyncio

    async def _test():
        print("Connecting to MongoDB...")
        try:
            await connect()
            print("Connected successfully to MongoDB! MongoDB is ready.")
        except Exception as e:
            print("Connection failed:", e)
        finally:
            await close()

    asyncio.run(_test())
