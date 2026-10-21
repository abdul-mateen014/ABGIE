import asyncio
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.api.routes import auth
from app.models.schemas import LoginRequest, RegisterRequest


def test_password_hash_and_signed_token():
    password_hash = auth._password_hash("a-secure-password")
    assert auth._verify_password("a-secure-password", password_hash)
    assert not auth._verify_password("wrong-password", password_hash)

    user_id = str(ObjectId())
    token = auth._create_access_token(user_id)
    assert auth._token_subject(token) == user_id
    with pytest.raises(HTTPException):
        auth._token_subject(f"{token[:-1]}x")


def test_register_and_login_store_password_hash(monkeypatch):
    class FakeUsers:
        def __init__(self):
            self.documents = {}

        async def create_index(self, *args, **kwargs):
            return "email_unique"

        async def insert_one(self, document):
            if document["email"] in self.documents:
                raise DuplicateKeyError("duplicate email")
            document = {**document, "_id": ObjectId()}
            self.documents[document["email"]] = document
            return SimpleNamespace(inserted_id=document["_id"])

        async def find_one(self, query):
            return self.documents.get(query["email"])

    users = FakeUsers()
    monkeypatch.setattr(auth.mongo, "get_db", lambda: SimpleNamespace(users=users))

    registered = asyncio.run(
        auth.register(RegisterRequest(email=" Test@Example.com ", name=" Test User ", password="a-secure-password"))
    )
    stored_user = users.documents["test@example.com"]
    assert registered.user.email == "test@example.com"
    assert stored_user["password_hash"] != "a-secure-password"

    logged_in = asyncio.run(
        auth.login(LoginRequest(email="TEST@example.com", password="a-secure-password"))
    )
    assert logged_in.user.id == registered.user.id
