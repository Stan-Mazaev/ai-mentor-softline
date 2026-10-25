from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai-mentor"
    app_env: str = "dev"
    log_level: str = "INFO"

    # Если задан — используем как есть (SQLite локально, Postgres в Docker)
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_user: str = "mentor"
    postgres_password: str = "mentor"
    postgres_db: str = "mentor"

    redis_host: str = "redis"
    redis_port: int = 6379

    # LLM
    llm_provider: str = "stub"
    llm_api_key: str = ""
    llm_model: str = ""

    # --- Новые настройки LLM ---
    llm_cache_ttl: int = 300
    llm_circuit_failure_threshold: int = 3
    llm_circuit_reset_seconds: float = 30.0
    llm_max_tokens: int = 512
    # ---------------------------

    pii_masking_enabled: bool = True
    disclaimer_enabled: bool = True

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()