from __future__ import annotations

import base64
import json
from typing import Any

from .models import PubSubNotification


class PubSubPayloadError(ValueError):
    pass


def parse_pubsub_push(payload: dict[str, Any]) -> PubSubNotification:
    message = payload.get("message")
    if not isinstance(message, dict):
        raise PubSubPayloadError("Pub/Sub payload is missing message")

    pubsub_message_id = str(message.get("messageId") or message.get("message_id") or "")
    encoded_data = message.get("data")
    if not pubsub_message_id or not encoded_data:
        raise PubSubPayloadError("Pub/Sub message is missing messageId or data")

    try:
        decoded = base64.b64decode(encoded_data).decode("utf-8")
        gmail_event = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PubSubPayloadError("Pub/Sub message data is not valid Gmail JSON") from exc

    email_address = str(gmail_event.get("emailAddress") or "")
    history_id = str(gmail_event.get("historyId") or "")
    if not email_address or not history_id:
        raise PubSubPayloadError("Gmail notification is missing emailAddress or historyId")

    return PubSubNotification(
        pubsub_message_id=pubsub_message_id,
        email_address=email_address,
        history_id=history_id,
    )

