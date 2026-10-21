import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time

from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.db import mongo
from app.models.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    User,
    UserPublic,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)
TOKEN_LIFETIME_SECONDS = 12 * 60 * 60
PASSWORD_ITERATIONS = 310_000


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_encode(salt)}${_encode(digest)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256" or int(rounds) != PASSWORD_ITERATIONS:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _decode(salt), PASSWORD_ITERATIONS
        )
        return hmac.compare_digest(_encode(digest), expected)
    except (ValueError, TypeError):
        return False


def _create_access_token(user_id: str) -> str:
    claims = {"sub": user_id, "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS}
    payload = _encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"), payload.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{payload}.{_encode(signature)}"


def _token_subject(token: str) -> str:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(
            settings.auth_secret_key.encode("utf-8"), payload.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_decode(signature), expected):
            raise ValueError
        claims = json.loads(_decode(payload))
        if not isinstance(claims.get("sub"), str) or claims.get("exp", 0) <= time.time():
            raise ValueError
        return claims["sub"]
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, binascii.Error):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    try:
        user_id = mongo.oid(_token_subject(credentials.credentials))
    except InvalidId:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    user = await mongo.get_db().users.find_one({"_id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    return user


def _auth_response(user: dict) -> AuthResponse:
    user_id = str(user["_id"])
    return AuthResponse(
        access_token=_create_access_token(user_id),
        user=UserPublic(id=user_id, email=user["email"], name=user["name"]),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    db = mongo.get_db()
    await db.users.create_index("email", unique=True)
    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=_password_hash(payload.password),
    )
    try:
        result = await db.users.insert_one(user.to_mongo())
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    return _auth_response({"_id": result.inserted_id, "email": user.email, "name": user.name})


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    user = await mongo.get_db().users.find_one({"email": payload.email})
    if user is None or not _verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _auth_response(user)


@router.get("/me", response_model=UserPublic)
async def current_user(user: dict = Depends(get_current_user)):
    return UserPublic(id=str(user["_id"]), email=user["email"], name=user["name"])