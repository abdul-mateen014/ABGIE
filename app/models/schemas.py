"""Data models for ABGIE: one Pydantic model per MongoDB collection.

Collection names and indexed fields match app/db/init_db.py.
Fields that are not indexed there are proposals based on the FYP proposal;
check them against the ERD and adjust.
"""
from datetime import datetime, timezone
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


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
class Brand(MongoModel):
    user_id: PyId                   # index
    name: str
    industry: str
    description: Optional[str] = None
    target_audience: str
    goals: list[str] = []           # e.g. engagement, reach
    tone: Optional[str] = None
    city: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class SocialAccount(MongoModel):
    brand_id: PyId                  # index
    platform: Platform
    username: str
    external_id: Optional[str] = None   # Instagram user id / Facebook page id
    access_token: Optional[str] = None  # never log or commit this
    created_at: datetime = Field(default_factory=utcnow)


# ----------------------------------------------------------- competitors
class Competitor(MongoModel):
    brand_id: PyId                  # unique together with place_id
    place_id: str                   # Google Places id
    name: str
    address: Optional[str] = None
    rating: Optional[float] = None
    instagram_username: Optional[str] = None
    followers_count: int = 0
    avg_engagement_rate: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)


class CompetitorPost(MongoModel):
    competitor_id: PyId             # index with posted_at
    platform: Platform = "instagram"
    caption: Optional[str] = None
    hashtags: list[str] = []
    media_type: Optional[str] = None
    like_count: int = 0
    comments_count: int = 0
    posted_at: datetime


# ----------------------------------------------------------- intelligence
class IntelligenceReport(MongoModel):
    brand_id: PyId                  # index with created_at
    brand_tone: Optional[str] = None
    competitor_benchmark: dict[str, Any] = {}
    trends: list[str] = []
    audience_clusters: list[dict[str, Any]] = []
    strategy_object: dict[str, Any] = {}    # structured output of Step 2
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
    created_at: datetime = Field(default_factory=utcnow)

    @staticmethod
    def compute_score(weight: float, confidence: float, risk_penalty: float) -> float:
        """Weighted decision score = (weight x confidence) - risk penalty."""
        return weight * confidence - risk_penalty


# ------------------------------------------------------------- execution
class ContentItem(MongoModel):
    strategy_id: PyId               # index with status
    platform: Platform
    caption: str
    cta: Optional[str] = None
    hashtags: list[str] = []
    media_url: Optional[str] = None
    status: Literal["draft", "approved", "queued", "published", "failed"] = "draft"
    created_at: datetime = Field(default_factory=utcnow)


class QueueEntry(MongoModel):
    content_id: PyId                # index
    platform: Platform
    scheduled_time: datetime        # index
    status: Literal["queued", "published", "failed"] = "queued"
    published_at: Optional[datetime] = None
    external_post_id: Optional[str] = None
    error: Optional[str] = None


# -------------------------------------------------------------- learning
class Metric(MongoModel):
    queue_id: PyId                  # index
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
    weights: dict[str, float] = {}
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
    decision_id: Optional[PyId] = None  # index
    decision_type: str
    reasoning: str
    created_at: datetime = Field(default_factory=utcnow)
