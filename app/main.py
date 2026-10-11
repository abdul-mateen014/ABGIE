from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import mongo

@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo.connect()
    yield
    await mongo.close()

app = FastAPI(title="ABGIE", lifespan=lifespan)

@app.get("/health")
async def health():
    await mongo.client.admin.command("ping")
    return {"status": "ok", "db": "connected"}