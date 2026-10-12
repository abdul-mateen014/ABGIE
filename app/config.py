# Configuration settings
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_uri: str
    mongodb_db: str = "abgie"
    google_places_api_key: str = ""
    places_monthly_limit: int = 900
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()