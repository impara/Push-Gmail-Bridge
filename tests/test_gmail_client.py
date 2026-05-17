import base64

from hermes_gmail_bridge.gmail_client import _extract_bodies


def b64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def test_extract_bodies_walks_nested_mime_parts():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "multipart/related",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": b64url("hello text")}},
                    {"mimeType": "text/html", "body": {"data": b64url("<p>hello html</p>")}},
                ],
            }
        ],
    }

    text, html = _extract_bodies(payload)

    assert text == "hello text"
    assert html == "<p>hello html</p>"

