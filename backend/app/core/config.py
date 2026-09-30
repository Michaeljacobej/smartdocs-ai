from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Document Processing Portal"
    app_env: str = "dev"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/document_ai",
        alias="DATABASE_URL",
    )
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    llm_model: str = Field(default="qwen3", alias="LLM_MODEL")
    ollama_timeout_seconds: float = Field(default=300.0, alias="OLLAMA_TIMEOUT_SECONDS")

    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(default=10, alias="MAX_FILE_SIZE_MB")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
