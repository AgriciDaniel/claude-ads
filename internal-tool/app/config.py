"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Ads API
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    google_ads_login_customer_id: str = ""  # For MCC accounts

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/claude_ads"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    secret_key: str = "change-me-to-a-random-string"
    app_env: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
