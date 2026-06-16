from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "postgresql+psycopg://ege:ege@localhost:5433/ege_mentor"
    api_cors_origins: str = "http://localhost:5174,http://127.0.0.1:5174"
    invite_bootstrap_code: str = "family-pilot"

    llm_provider: str = "disabled"
    openai_compat_base_url: str = "http://localhost:8000/v1"
    openai_compat_api_key: str = Field(default="change-me", repr=False)
    openai_compat_model: str = "qwen-local"

    telegram_bot_token: str = Field(default="", repr=False)
    public_api_base_url: str = "http://localhost:8001"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.api_cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
