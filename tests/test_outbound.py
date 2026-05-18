import base64
from email import message_from_bytes

from fastapi.testclient import TestClient

from hermes_gmail_bridge.app import create_app
from hermes_gmail_bridge.config import Settings
from hermes_gmail_bridge.gmail_client import GmailClient
from hermes_gmail_bridge.models import EmailMessage


class FakeMessagesResource:
    def __init__(self):
        self.sent_body = None

    def send(self, userId, body):
        self.sent_body = body
        return self

    def execute(self):
        return {"id": "sent-1", "threadId": self.sent_body["threadId"]}


class FakeUsersResource:
    def __init__(self, messages_resource):
        self.messages_resource = messages_resource

    def messages(self):
        return self.messages_resource


class FakeService:
    def __init__(self):
        self.messages_resource = FakeMessagesResource()

    def users(self):
        return FakeUsersResource(self.messages_resource)


class FakeGmailClient(GmailClient):
    def __init__(self):
        self.fake_service = FakeService()

    @property
    def service(self):
        return self.fake_service

    def get_message(self, message_id):
        return EmailMessage(
            gmail_id=message_id,
            thread_id="thread-1",
            history_id="history-1",
            from_addr="Sender <sender@example.com>",
            to_addrs=["contact@example.com"],
            subject="Hello",
            received_at="2026-05-18T00:00:00+00:00",
            text="Original",
            headers={"message-id": "<original@example.com>", "references": "<prev@example.com>"},
        )


def test_outbound_reply_requires_token(tmp_path):
    settings = Settings(
        sqlite_path=tmp_path / "bridge.sqlite3",
        hermes_webhook_url="http://hermes.test/webhooks/contact-inbox",
    )
    client = TestClient(create_app(settings))

    response = client.post("/outbound/reply", json={"original_message_id": "m1", "text": "Hi"})

    assert response.status_code == 503


def test_outbound_reply_sends_threaded_mime(tmp_path):
    settings = Settings(
        sqlite_path=tmp_path / "bridge.sqlite3",
        public_inbox_address="contact@example.com",
        hermes_webhook_url="http://hermes.test/webhooks/contact-inbox",
        hermes_outbound_token="secret",
    )
    app = create_app(settings)
    fake_gmail = FakeGmailClient()
    app.state.gmail = fake_gmail
    client = TestClient(app)

    response = client.post(
        "/outbound/reply",
        headers={"Authorization": "Bearer secret"},
        json={"original_message_id": "m1", "text": "Approved reply"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "sent", "message_id": "sent-1", "thread_id": "thread-1"}

    raw = fake_gmail.fake_service.messages_resource.sent_body["raw"]
    decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
    mime = message_from_bytes(decoded)
    assert fake_gmail.fake_service.messages_resource.sent_body["threadId"] == "thread-1"
    assert mime["From"] == "contact@example.com"
    assert mime["To"] == "sender@example.com"
    assert mime["Subject"] == "Re: Hello"
    assert mime["In-Reply-To"] == "<original@example.com>"
    assert mime["References"] == "<prev@example.com> <original@example.com>"

