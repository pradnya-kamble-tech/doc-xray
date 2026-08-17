"""Application configuration loaded from environment variables."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    frontend_url: str = "http://localhost:3000"

    upload_dir: Path = BASE_DIR / "data" / "uploads"
    chroma_dir: Path = BASE_DIR / "data" / "chroma"
    sqlite_dir: Path = BASE_DIR / "data" / "sqlite"
    sqlite_url: str = ""

    max_upload_size_mb: int = 20

    class Config:
        env_file = BASE_DIR.parent.parent / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def model_post_init(self, __context) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_dir.mkdir(parents=True, exist_ok=True)
        if not self.sqlite_url:
            self.sqlite_url = f"sqlite+aiosqlite:///{self.sqlite_dir / 'docxray.db'}"


settings = Settings()
