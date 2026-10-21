import asyncio
from types import SimpleNamespace

from bson import ObjectId
from fastapi import HTTPException
import pytest

from app.api.routes import brands
from app.models.schemas import BrandCreate


def test_create_brand_saves_form_fields_and_user_id(monkeypatch):
    inserted = {}

    class FakeBrands:
        existing = None

        async def find_one(self, query):
            return self.existing

        async def insert_one(self, document):
            inserted.update(document)
            return SimpleNamespace(inserted_id=ObjectId())

    user_id = ObjectId()
    monkeypatch.setattr(brands.mongo, "get_db", lambda: SimpleNamespace(brands=FakeBrands()))
    payload = BrandCreate(
        name="Cafe X",
        industry="specialty coffee",
        products=["coffee", "pastries"],
        website="https://example.com",
        city="Lahore",
        lat=31.5204,
        lng=74.3587,
        radius_km=5,
        target_audience="students",
        goals=["reach", "engagement"],
        platforms=["instagram", "facebook"],
    )

    saved = asyncio.run(brands.create_brand(payload, {"_id": user_id}))

    assert inserted["user_id"] == str(user_id)
    assert inserted["name"] == "Cafe X"
    assert inserted["lat"] == 31.5204
    assert inserted["platforms"] == ["instagram", "facebook"]
    assert saved.id is not None


def test_duplicate_brand_name_is_rejected(monkeypatch):
    class FakeBrands:
        async def find_one(self, query):
            return {"_id": ObjectId(), "name": "CAFE X"}

        async def insert_one(self, document):
            raise AssertionError("duplicate brand must not be inserted")

    monkeypatch.setattr(brands.mongo, "get_db", lambda: SimpleNamespace(brands=FakeBrands()))
    payload = BrandCreate(
        name="Cafe X",
        industry="cafe",
        target_audience="students",
        city="Lahore",
        lat=31.52,
        lng=74.35,
        radius_km=5,
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(brands.create_brand(payload, {"_id": ObjectId()}))
    assert error.value.status_code == 409


def test_blank_website_is_stored_as_null():
    payload = BrandCreate(
        name=" Cafe X ",
        industry="cafe",
        website="   ",
        target_audience="students",
        city="Lahore",
        lat=31.52,
        lng=74.35,
        radius_km=5,
    )
    assert payload.name == "Cafe X"
    assert payload.website is None


def test_delete_brand_is_scoped_to_owner(monkeypatch):
    deleted_query = {}

    class FakeBrands:
        async def delete_one(self, query):
            deleted_query.update(query)
            return SimpleNamespace(deleted_count=1)

    brand_id = ObjectId()
    user_id = ObjectId()
    monkeypatch.setattr(brands.mongo, "get_db", lambda: SimpleNamespace(brands=FakeBrands()))

    response = asyncio.run(brands.delete_brand(str(brand_id), {"_id": user_id}))

    assert response.status_code == 204
    assert deleted_query == {"_id": brand_id, "user_id": str(user_id)}