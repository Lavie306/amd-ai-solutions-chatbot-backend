from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: Literal["development", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/amd_chatbot.db"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "amd_knowledge_base"

    # SendGrid
    sendgrid_api_key: str = ""
    email_from: str = "noreply@amd.vn"
    email_from_name: str = "AMD AI Solutions"
    email_notify_to: str = "team@amd.vn"

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    # Admin seed
    admin_email: str = "admin@amd.vn"
    admin_password: str = "changeme123"

    # Rate limiting
    rate_limit_chat: int = 30
    rate_limit_api: int = 60

    # Scheduler
    scheduler_timezone: str = "Asia/Ho_Chi_Minh"


@lru_cache
def get_settings() -> Settings:
    return Settings()
