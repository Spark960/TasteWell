"""Env schema (IMPLEMENTATION.md §4). Fail fast on missing Qloo key outside dev."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingCredential(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "dev"
    backend_port: int = 8000
    frontend_port: int = 3000

    qloo_api_key: str = ""
    qloo_base_url: str = "https://hackathon.api.qloo.com"
    qloo_trusted_base_url: str = "https://hackathon.api.qloo.com"
    qloo_bin: str = "qloo"
    qloo_timeout_s: float = 60.0
    qloo_cache_ttl_s: float = 600.0
    qloo_max_retries: int = 2

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""

    def require_qloo_key(self) -> str:
        if not self.qloo_api_key and self.app_env != "dev":
            raise MissingCredential(
                "QLOO_API_KEY is not set (required when APP_ENV != dev)"
            )
        return self.qloo_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
