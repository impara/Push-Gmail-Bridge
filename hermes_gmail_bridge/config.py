from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    public_inbox_address: str = Field(default="contact@example.com")
    gmail_account: str = Field(default="agent-inbox@gmail.com")

    google_credentials_file: Path = Field(default=Path("secrets/google-oauth-client.json"))
    google_token_file: Path = Field(default=Path("secrets/google-token.json"))
    google_pubsub_topic: str = Field(default="")
    gmail_label_ids: str = Field(default="INBOX")

    sqlite_path: Path = Field(default=Path("data/bridge.sqlite3"))

    hermes_webhook_url: AnyHttpUrl = Field(default="http://localhost:8080/webhooks/contact-inbox")
    hermes_webhook_token: str = Field(default="")
    hermes_timeout_seconds: float = Field(default=10.0)

    pubsub_audience: str = Field(default="")
    pubsub_bearer_token: str = Field(default="")

    max_history_results: int = Field(default=50)
    recovery_query: str = Field(default="newer_than:3d")

    @property
    def label_ids(self) -> list[str]:
        return [label.strip() for label in self.gmail_label_ids.split(",") if label.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
