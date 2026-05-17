from pathlib import Path

import pytest

from hermes_gmail_bridge.config import Settings
from hermes_gmail_bridge.models import EmailMessage, PubSubNotification
from hermes_gmail_bridge.processor import LAST_HISTORY_ID, NotificationProcessor
from hermes_gmail_bridge.state import StateStore


class FakeGmail:
    def __init__(self):
        self.history_calls = []
        self.messages = {
            "m1": EmailMessage(
                gmail_id="m1",
                thread_id="t1",
                history_id="101",
                from_addr="A <a@example.com>",
                to_addrs=["contact@example.com"],
                subject="Hi",
                received_at="2026-05-17T12:00:00+00:00",
                text="Hello",
            )
        }

    def list_history(self, start_history_id, max_results=50):
        self.history_calls.append((start_history_id, max_results))
        return ["m1", "m1"], "101"

    def get_message(self, message_id):
        return self.messages[message_id]


class FakeHermes:
    def __init__(self):
        self.payloads = []

    async def deliver(self, payload):
        self.payloads.append(payload)


@pytest.mark.asyncio
async def test_processor_uses_history_and_dedupes_messages(tmp_path: Path):
    settings = Settings(
        sqlite_path=tmp_path / "bridge.sqlite3",
        hermes_webhook_url="http://hermes.test/webhooks/contact-inbox",
    )
    state = StateStore(settings.sqlite_path)
    state.set(LAST_HISTORY_ID, "100")
    gmail = FakeGmail()
    hermes = FakeHermes()
    processor = NotificationProcessor(settings, state, gmail, hermes)

    await processor.process(PubSubNotification("pubsub-1", "agent-inbox@gmail.com", "101"))

    assert gmail.history_calls == [("100", 50)]
    assert len(hermes.payloads) == 1
    assert hermes.payloads[0]["message_id"] == "m1"
    assert state.get(LAST_HISTORY_ID) == "101"


@pytest.mark.asyncio
async def test_processor_initializes_cursor_without_forwarding(tmp_path: Path):
    settings = Settings(
        sqlite_path=tmp_path / "bridge.sqlite3",
        hermes_webhook_url="http://hermes.test/webhooks/contact-inbox",
    )
    state = StateStore(settings.sqlite_path)
    gmail = FakeGmail()
    hermes = FakeHermes()
    processor = NotificationProcessor(settings, state, gmail, hermes)

    await processor.process(PubSubNotification("pubsub-1", "agent-inbox@gmail.com", "101"))

    assert state.get(LAST_HISTORY_ID) == "101"
    assert hermes.payloads == []
