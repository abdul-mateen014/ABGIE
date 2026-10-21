from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routes import auth, brands
from app.db import mongo

@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo.connect()
    yield
    await mongo.close()

app = FastAPI(title="ABGIE", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(brands.router)


@app.get("/", include_in_schema=False)
async def home():
    frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    return FileResponse(frontend_path)

@app.get("/health")
async def health():
    await mongo.client.admin.command("ping")
    return {"status": "ok", "db": "connected"}