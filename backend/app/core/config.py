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
    llm_model: str = Field(default="qwen2.5:0.5b", alias="LLM_MODEL")
    llm_summary_model: str | None = Field(default="qwen2.5:0.5b", alias="LLM_SUMMARY_MODEL")
    llm_summary_fallback_model: str | None = Field(default="qwen2.5:0.5b", alias="LLM_SUMMARY_FALLBACK_MODEL")
    ollama_timeout_seconds: float = Field(default=120.0, alias="OLLAMA_TIMEOUT_SECONDS")
    ollama_summary_timeout_seconds: float = Field(default=60.0, alias="OLLAMA_SUMMARY_TIMEOUT_SECONDS")
    ollama_keep_alive: str = Field(default="10m", alias="OLLAMA_KEEP_ALIVE")
    ollama_think: bool = Field(default=False, alias="OLLAMA_THINK")
    ollama_retry_attempts: int = Field(default=2, alias="OLLAMA_RETRY_ATTEMPTS")
    ollama_retry_backoff_seconds: float = Field(default=0.2, alias="OLLAMA_RETRY_BACKOFF_SECONDS")
    ollama_num_predict: int = Field(default=64, alias="OLLAMA_NUM_PREDICT")
    ollama_num_ctx: int = Field(default=1024, alias="OLLAMA_NUM_CTX")
    ollama_temperature: float = Field(default=0.1, alias="OLLAMA_TEMPERATURE")
    ollama_summary_num_predict: int = Field(default=200, alias="OLLAMA_SUMMARY_NUM_PREDICT")
    ollama_summary_num_ctx: int = Field(default=2048, alias="OLLAMA_SUMMARY_NUM_CTX")
    ollama_summary_temperature: float = Field(default=0.1, alias="OLLAMA_SUMMARY_TEMPERATURE")

    ocr_max_pages: int = Field(default=2, alias="OCR_MAX_PAGES")
    ocr_searchable_text_threshold: int = Field(default=400, alias="OCR_SEARCHABLE_TEXT_THRESHOLD")

    summary_max_ocr_chars: int = Field(default=20000, alias="SUMMARY_MAX_OCR_CHARS")
    summary_reuse_existing: bool = Field(default=True, alias="SUMMARY_REUSE_EXISTING")

    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(default=10, alias="MAX_FILE_SIZE_MB")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        upload_dir = Path(self.upload_dir)
        if not upload_dir.is_absolute():
            backend_root = Path(__file__).resolve().parents[2]
            upload_dir = backend_root / upload_dir
        return upload_dir.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
