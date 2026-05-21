from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from .approval_labels import build_approval_label
from .models import EmailMessage


class HermesDeliveryError(RuntimeError):
    pass


class HermesClient:
    def __init__(self, webhook_url: str, token: str = "", timeout_seconds: float = 10.0):
        self.webhook_url = webhook_url
        self.token = token
        self.timeout_seconds = timeout_seconds

    async def deliver(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        headers = {"content-type": "application/json"}
        if self.token:
            headers["x-webhook-signature"] = hmac.new(
                self.token.encode(), body, hashlib.sha256
            ).hexdigest()

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.webhook_url, headers=headers, content=body)

        if response.status_code >= 300:
            raise HermesDeliveryError(f"Hermes returned HTTP {response.status_code}: {response.text[:500]}")


def build_contact_inbox_payload(
    message: EmailMessage,
    public_inbox_address: str,
    gmail_account: str,
) -> dict[str, Any]:
    return {
        "source": "gmail",
        "inbox": public_inbox_address,
        "gmail_account": gmail_account,
        "message_id": message.gmail_id,
        "approval_label": build_approval_label(message.gmail_id),
        "rfc822_message_id": message.header_message_id,
        "thread_id": message.thread_id,
        "history_id": message.history_id,
        "from": message.from_addr,
        "to": message.to_addrs,
        "cc": message.cc_addrs,
        "subject": message.subject,
        "received_at": message.received_at,
        "text": message.text,
        "html": message.html,
        "headers": {
            "message_id": message.headers.get("message-id", ""),
            "in_reply_to": message.headers.get("in-reply-to", ""),
            "references": message.headers.get("references", ""),
            "reply_to": message.headers.get("reply-to", ""),
        },
        "raw": {
            "snippet": message.raw.get("snippet", ""),
            "label_ids": message.raw.get("labelIds", []),
        },
    }


def payload_to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)

