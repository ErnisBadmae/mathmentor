from dataclasses import dataclass
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class LlmConnection:
    """Resolved OpenAI-compatible endpoint for the active local provider."""

    base_url: str
    api_key: str
    model: str
    timeout: float


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "postgresql+psycopg://ege:ege@localhost:5434/ege_mentor"
    api_cors_origins: str = "http://localhost:5174,http://127.0.0.1:5174"
    api_shared_token: str = ""
    invite_bootstrap_code: str = "family-pilot"
    local_timezone: str = "Europe/Moscow"

    # Local LLM provider switch: disabled | vllm | llama_cpp. Both vllm and llama.cpp
    # expose the same OpenAI-compatible /v1/chat/completions, so one reviewer serves both.
    llm_provider: str = "disabled"

    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_api_key: str = Field(default="token-abc123", repr=False)
    vllm_model: str = "qwen-local"
    vllm_timeout: float = 120

    llama_cpp_base_url: str = "http://192.168.0.18:8000/v1"
    llama_cpp_api_key: str = Field(default="token-abc123", repr=False)
    llama_cpp_model: str = "Qwen3.6-35B-A3B-Q5-256K"
    llama_cpp_timeout: float = 120

    telegram_bot_token: str = Field(default="", repr=False)
    public_api_base_url: str = "http://localhost:8001"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.api_cors_origins.split(",") if item.strip()]

    def llm_connection(self) -> LlmConnection | None:
        """Return the active provider's endpoint, or None when LLM review is disabled."""
        if self.llm_provider == "vllm":
            return LlmConnection(
                self.vllm_base_url, self.vllm_api_key, self.vllm_model, self.vllm_timeout
            )
        if self.llm_provider == "llama_cpp":
            return LlmConnection(
                self.llama_cpp_base_url,
                self.llama_cpp_api_key,
                self.llama_cpp_model,
                self.llama_cpp_timeout,
            )
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
