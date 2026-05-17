from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


@dataclass(frozen=True)
class PubSubNotification:
    pubsub_message_id: str
    email_address: str
    history_id: str


@dataclass(frozen=True)
class EmailMessage:
    gmail_id: str
    thread_id: str
    history_id: str | None
    from_addr: str
    to_addrs: list[str]
    cc_addrs: list[str] = field(default_factory=list)
    subject: str = ""
    received_at: str = ""
    text: str = ""
    html: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def header_message_id(self) -> str:
        return self.headers.get("message-id", "")


def normalize_email_date(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, AttributeError):
        return datetime.now(timezone.utc).isoformat()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()

