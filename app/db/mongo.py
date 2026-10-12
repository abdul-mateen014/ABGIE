from pymongo import AsyncMongoClient
from app.config import settings

client: AsyncMongoClient | None = None

async def connect():
    global client
    client = AsyncMongoClient(settings.mongodb_uri)
    await client.admin.command("ping")   # fails here if the connection is wrong

async def close():
    if client:
        await client.close()

def get_db():
    return client[settings.mongodb_db]