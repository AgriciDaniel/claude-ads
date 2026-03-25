"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Ads API
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_redirect_uri: str = "http://localhost:8000/api/auth/callback"
    google_ads_login_customer_id: str = ""  # For MCC accounts

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ads_audit"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    secret_key: str = "change-me-to-a-random-string"
    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"

    # JWT
    jwt_secret: str = "change-me-to-a-random-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
