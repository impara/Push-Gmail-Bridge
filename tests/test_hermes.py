from hermes_gmail_bridge.hermes import build_contact_inbox_payload
from hermes_gmail_bridge.models import EmailMessage


def test_build_contact_inbox_payload_is_clean_json_contract():
    message = EmailMessage(
        gmail_id="gmail-1",
        thread_id="thread-1",
        history_id="history-1",
        from_addr="Sender <sender@example.com>",
        to_addrs=["contact@example.com"],
        subject="Hello",
        received_at="2026-05-17T12:00:00+00:00",
        text="Plain body",
        html="<p>Plain body</p>",
        headers={"message-id": "<abc@example.com>", "in-reply-to": "<prev@example.com>"},
        raw={"snippet": "Plain", "labelIds": ["INBOX"]},
    )

    payload = build_contact_inbox_payload(message, "contact@example.com", "agent-inbox@gmail.com")

    assert payload["source"] == "gmail"
    assert payload["inbox"] == "contact@example.com"
    assert payload["message_id"] == "gmail-1"
    assert payload["rfc822_message_id"] == "<abc@example.com>"
    assert payload["headers"]["in_reply_to"] == "<prev@example.com>"
    assert payload["raw"]["label_ids"] == ["INBOX"]
