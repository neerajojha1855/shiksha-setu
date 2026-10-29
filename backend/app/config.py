from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    app_name: str = "Shiksha Setu API"
    api_prefix: str = "/api"
    frontend_origin: str = "http://localhost:5173"
    database_url: str = ""
    direct_database_url: str = Field(
        default="",
        validation_alias=AliasChoices("DIRECT_DATABASE_URL", "DATABASE_URL_UNPOOLED"),
    )
    jwt_secret_key: str = "development-only-change-this-secret"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen3:8b"
    ollama_api_key: str = ""
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder: str = "shiksha-setu/donations"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
