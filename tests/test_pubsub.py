import base64
import json

import pytest

from hermes_gmail_bridge.pubsub import PubSubPayloadError, parse_pubsub_push


def test_parse_pubsub_push_decodes_gmail_notification():
    data = base64.b64encode(
        json.dumps({"emailAddress": "agent-inbox@gmail.com", "historyId": "123"}).encode()
    ).decode()

    notification = parse_pubsub_push({"message": {"messageId": "pubsub-1", "data": data}})

    assert notification.pubsub_message_id == "pubsub-1"
    assert notification.email_address == "agent-inbox@gmail.com"
    assert notification.history_id == "123"


def test_parse_pubsub_push_rejects_missing_history_id():
    data = base64.b64encode(json.dumps({"emailAddress": "agent-inbox@gmail.com"}).encode()).decode()

    with pytest.raises(PubSubPayloadError):
        parse_pubsub_push({"message": {"messageId": "pubsub-1", "data": data}})
