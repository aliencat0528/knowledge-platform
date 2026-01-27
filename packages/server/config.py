"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_path: str = "./data/knowledge.db"
    chroma_path: str = "./data/chroma"

    # API Keys (optional)
    openai_api_key: str | None = None
    notion_api_key: str | None = None
    notion_database_id: str | None = None

    # API Authentication (optional)
    api_key: str | None = None

    # Embedding
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    auto_embed: bool = False  # Auto-embed new articles on import

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def database_url(self) -> str:
        """Get SQLite database URL."""
        return f"sqlite+aiosqlite:///{self.database_path}"

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        return Path(self.database_path).parent

    def ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
