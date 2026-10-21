"""Data models for ABGIE: one Pydantic model per MongoDB collection.
Collection names and indexed fields match app/db/init_db.py.
"""
from datetime import datetime, timezone
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_str(v: Any) -> Any:
    """Turn a Mongo ObjectId into a plain string."""
    return str(v) if v is not None else v


# String id that also accepts a Mongo ObjectId.
PyId = Annotated[str, BeforeValidator(_to_str)]

Platform = Literal["instagram", "facebook"]


class MongoModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: Optional[PyId] = Field(default=None, alias="_id")

    def to_mongo(self) -> dict:
        """Dict ready for insert_one(); omits _id and None values."""
        return self.model_dump(by_alias=True, exclude_none=True)


# ---------------------------------------------------------------- users
class User(MongoModel):
    email: str                      # unique index
    name: str
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------- brands
class BrandBase(BaseModel):
    """Fields the user fills in the brand form."""
    name: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    description: Optional[str] = None
    website: Optional[str] = None
    products: list[str] = []
    target_audience: str
    goals: list[str] = []                   # e.g. engagement, reach
    platforms: list[Platform] = []
    posts_per_week: Optional[int] = Field(default=None, ge=1, le=50)
    tone: Optional[str] = None
    city: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_km: float = Field(gt=0, le=50)   # check Google's current max radius

    @field_validator("name", "industry", "target_audience", "city")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("website", mode="before")
    @classmethod
    def normalize_website(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class BrandCreate(BrandBase):
    """What the API accepts from the form (no user_id, no created_at)."""


class Brand(MongoModel, BrandBase):
    user_id: PyId                   # index
    created_at: datetime = Field(default_factory=utcnow)


class SocialAccount(MongoModel):
    brand_id: PyId                  # index
    platform: Platform
    username: str
    external_id: Optional[str] = None       # Instagram user id / Facebook page id
    access_token_encrypted: Optional[str] = None  # encrypted before saving, never log
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)


# ----------------------------------------------------------- competitors
class Competitor(MongoModel):
    brand_id: PyId                  # unique together with place_id
    place_id: str                   # Google Places id
    name: str
    address: Optional[str] = None
    distance_km: Optional[float] = None
    category: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: int = 0
    instagram_username: Optional[str] = None
    followers_count: int = 0
    avg_engagement_rate: float = 0.0
    status: Literal["discovered", "analysed", "no_public_instagram"] = "discovered"
    created_at: datetime = Field(default_factory=utcnow)


class CompetitorPost(MongoModel):
    competitor_id: PyId             # unique together with external_id
    external_id: str                # Instagram media id (stops duplicate saves)
    platform: Platform = "instagram"
    caption: Optional[str] = None
    hashtags: list[str] = []
    media_type: Optional[str] = None
    like_count: int = 0
    comments_count: int = 0
    engagement_rate: Optional[float] = None
    posted_at: datetime


# ----------------------------------------------------------- intelligence
class IntelligenceReport(MongoModel):
    brand_id: PyId                  # index with created_at
    brand_tone: Optional[str] = None
    competitor_benchmark: dict[str, Any] = {}
    trends: list[dict[str, Any]] = []       # {topic, hashtags, growth_pct}
    audience_clusters: list[dict[str, Any]] = []
    strategy_object: dict[str, Any] = {}    # structured output of P2
    confidence: float = Field(default=0, ge=0, le=100)
    created_at: datetime = Field(default_factory=utcnow)


class ContentStrategy(MongoModel):
    brand_id: PyId                  # index with status
    intelligence_id: PyId           # index
    platform: Optional[Platform] = None
    plan: dict[str, Any] = {}       # weekly / monthly plan
    strategy_weight: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=100)
    expected_performance: Optional[float] = None
    status: Literal["pending", "approved", "rejected"] = "pending"
    created_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------- decision
class RiskFactor(BaseModel):
    name: str                       # e.g. competitor activity
    severity: int = Field(ge=1, le=5)


class Decision(MongoModel):
    strategy_id: PyId               # index
    strategy_weight: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=100)
    risk_factors: list[RiskFactor] = []
    risk_penalty: float = Field(default=0, ge=0, le=10)
    score: Optional[float] = None
    threshold: Optional[float] = None
    approved: Optional[bool] = None
    reason: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)

    @staticmethod
    def compute_score(weight: float, confidence: float, risk_penalty: float) -> float:
        """Weighted decision score = (weight x confidence) - risk penalty."""
        return weight * confidence - risk_penalty


# ------------------------------------------------------------- execution
class ContentItem(MongoModel):
    strategy_id: PyId               # index with status
    platform: Platform
    content_type: Optional[str] = None      # image / reel / carousel
    theme: Optional[str] = None
    caption: str
    cta: Optional[str] = None
    hashtags: list[str] = []
    media_url: Optional[str] = None
    status: Literal["draft", "approved", "queued", "published", "failed"] = "draft"
    created_at: datetime = Field(default_factory=utcnow)


class QueueEntry(MongoModel):
    content_id: PyId                # index
    platform: Platform
    scheduled_time: datetime        # index with status
    status: Literal["queued", "published", "failed"] = "queued"
    retry_count: int = 0
    published_at: Optional[datetime] = None
    external_post_id: Optional[str] = None
    error: Optional[str] = None


# -------------------------------------------------------------- learning
class Metric(MongoModel):
    queue_id: PyId                  # index with collected_at
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0
    engagement_rate: float = 0.0
    expected_performance: Optional[float] = None
    deviation: Optional[float] = None
    collected_at: datetime = Field(default_factory=utcnow)

    @staticmethod
    def compute_engagement_rate(likes: int, comments: int, shares: int,
                                saves: int, reach: int) -> float:
        """Engagement rate = (likes + comments + shares + saves) / reach x 100."""
        return 0.0 if reach <= 0 else (likes + comments + shares + saves) / reach * 100

    @staticmethod
    def compute_deviation(expected: float, actual: float) -> float:
        """Strategy deviation = |expected - actual|."""
        return abs(expected - actual)


class StrategyWeights(MongoModel):
    brand_id: PyId                  # unique index
    version: int = 1
    weights: dict[str, float] = {}
    thresholds: dict[str, float] = {}       # approval, deviation
    updated_at: datetime = Field(default_factory=utcnow)


class AdaptationLog(MongoModel):
    brand_id: PyId                  # index with created_at
    trigger: str                    # e.g. "deviation above threshold"
    deviation: Optional[float] = None
    threshold: Optional[float] = None
    old_weights: dict[str, float] = {}
    new_weights: dict[str, float] = {}
    created_at: datetime = Field(default_factory=utcnow)


# ---------------------------------------------------------- transparency
class Explanation(MongoModel):
    brand_id: PyId                  # index
    decision_id: Optional[PyId] = None      # index
    decision_type: str
    reasoning: str
    created_at: datetime = Field(default_factory=utcnow)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserPublic(BaseModel):
    id: str
    email: str
    name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic