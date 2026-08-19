"""Application settings, loaded from environment variables only.

No credentials are hard-coded anywhere in this module or its callers;
see .env.example at the repo root for the full list of variables.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    app_env: str = Field(default="development", alias="APP_ENV")
    secret_key: str = Field(default="", alias="SECRET_KEY")
    database_url: str = Field(
        default="postgresql+psycopg://hermes:hermes@localhost:5432/hermes_leadgen",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"], alias="CORS_ORIGINS")

    # --- Auth ---
    access_token_expire_minutes: int = Field(default=60 * 12, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")

    # --- Secrets encryption (Fernet key for provider credentials at rest) ---
    credentials_encryption_key: str = Field(default="", alias="CREDENTIALS_ENCRYPTION_KEY")

    # --- Optional lead-source provider credentials (never required to run the MVP) ---
    google_places_api_key: str = Field(default="", alias="GOOGLE_PLACES_API_KEY")
    product_hunt_api_token: str = Field(default="", alias="PRODUCT_HUNT_API_TOKEN")
    github_token: str = Field(default="", alias="GITHUB_TOKEN")

    # --- AI provider (OpenAI-compatible; works with Ollama) ---
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="llama3.2:3b", alias="OPENAI_MODEL")
    openai_timeout_seconds: int = Field(default=30, alias="OPENAI_TIMEOUT_SECONDS")

    # --- Outreach sending (kept disabled by default; MVP is draft + CSV export only) ---
    outreach_live_send_enabled: bool = Field(default=False, alias="OUTREACH_LIVE_SEND_ENABLED")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_address: str = Field(default="", alias="SMTP_FROM_ADDRESS")

    # --- Sender identity used in generated outreach copy ---
    sender_name: str = Field(default="", alias="SENDER_NAME")
    sender_company: str = Field(default="Hermes Agent Services", alias="SENDER_COMPANY")
    sender_contact_email: str = Field(default="", alias="SENDER_CONTACT_EMAIL")

    # --- Compliance / retention ---
    lead_data_retention_days: int = Field(default=730, alias="LEAD_DATA_RETENTION_DAYS")

    # --- Research pipeline limits ---
    research_max_pages_per_domain: int = Field(default=5, alias="RESEARCH_MAX_PAGES_PER_DOMAIN")
    research_request_timeout_seconds: int = Field(default=10, alias="RESEARCH_REQUEST_TIMEOUT_SECONDS")
    research_requests_per_domain_per_minute: int = Field(default=6, alias="RESEARCH_REQUESTS_PER_DOMAIN_PER_MINUTE")
    research_llm_max_chars_per_page: int = Field(default=1500, alias="RESEARCH_LLM_MAX_CHARS_PER_PAGE")
    research_llm_max_pages: int = Field(default=2, alias="RESEARCH_LLM_MAX_PAGES")

    # --- Daily workflow defaults ---
    daily_discovery_lead_limit: int = Field(default=25, alias="DAILY_DISCOVERY_LEAD_LIMIT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
