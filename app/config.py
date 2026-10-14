# Configuration settings
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_uri: str
    mongodb_db: str = "abgie"
    google_places_api_key: str = ""
    places_monthly_limit: int = 900
    token_encryption_key: str = ""      # used when saving Meta tokens
    approval_threshold: float = 50      # Decision Layer: approve if score >= this
    deviation_threshold: float = 0.5    # Adaptive agent (later)
    max_retries: int = 3                # rejected strategy retries
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()