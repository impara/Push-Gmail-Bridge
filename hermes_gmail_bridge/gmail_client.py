from __future__ import annotations

import base64
from email.utils import getaddresses
from pathlib import Path
from typing import Any, Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import EmailMessage, normalize_email_date


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailHistoryExpired(RuntimeError):
    pass


class GmailClient:
    def __init__(self, credentials_file: Path, token_file: Path):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self._service = None

    @property
    def service(self):
        if self._service is None:
            self._service = build("gmail", "v1", credentials=self._load_credentials(), cache_discovery=False)
        return self._service

    def _load_credentials(self) -> Credentials:
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds or not creds.valid:
            if not self.credentials_file.exists():
                raise FileNotFoundError(f"Missing Google OAuth client file: {self.credentials_file}")
            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
            creds = flow.run_local_server(port=0)

        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def watch(self, topic_name: str, label_ids: list[str]) -> dict[str, Any]:
        body: dict[str, Any] = {"topicName": topic_name}
        if label_ids:
            body["labelIds"] = label_ids
            body["labelFilterBehavior"] = "INCLUDE"
        return self.service.users().watch(userId="me", body=body).execute()

    def stop_watch(self) -> None:
        self.service.users().stop(userId="me").execute()

    def list_history(self, start_history_id: str, max_results: int = 50) -> tuple[list[str], str | None]:
        message_ids: list[str] = []
        page_token = None
        latest_history_id: str | None = None

        while True:
            try:
                request = self.service.users().history().list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=["messageAdded"],
                    maxResults=max_results,
                    pageToken=page_token,
                )
                response = request.execute()
            except HttpError as exc:
                if exc.resp.status == 404:
                    raise GmailHistoryExpired("Gmail history cursor expired") from exc
                raise

            latest_history_id = str(response.get("historyId") or latest_history_id or "")
            for history_item in response.get("history", []):
                for added in history_item.get("messagesAdded", []):
                    message = added.get("message", {})
                    message_id = message.get("id")
                    if message_id:
                        message_ids.append(str(message_id))

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return _unique(message_ids), latest_history_id

    def list_recent_message_ids(self, query: str, max_results: int = 20) -> list[str]:
        response = self.service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results,
        ).execute()
        return [str(message["id"]) for message in response.get("messages", []) if message.get("id")]

    def get_message(self, message_id: str) -> EmailMessage:
        raw = self.service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()
        payload = raw.get("payload", {})
        headers = _headers_by_lower_name(payload.get("headers", []))
        text, html = _extract_bodies(payload)

        return EmailMessage(
            gmail_id=str(raw.get("id", "")),
            thread_id=str(raw.get("threadId", "")),
            history_id=str(raw.get("historyId", "")) if raw.get("historyId") else None,
            from_addr=headers.get("from", ""),
            to_addrs=_parse_addresses(headers.get("to", "")),
            cc_addrs=_parse_addresses(headers.get("cc", "")),
            subject=headers.get("subject", ""),
            received_at=normalize_email_date(headers.get("date")),
            text=text,
            html=html,
            headers=headers,
            raw=raw,
        )


def _headers_by_lower_name(headers: Iterable[dict[str, str]]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for header in headers:
        name = header.get("name")
        value = header.get("value")
        if name and value is not None:
            normalized[name.lower()] = value
    return normalized


def _parse_addresses(value: str) -> list[str]:
    return [address for _, address in getaddresses([value]) if address]


def _extract_bodies(payload: dict[str, Any]) -> tuple[str, str]:
    text_parts: list[str] = []
    html_parts: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime_type = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")

        if data and mime_type in {"text/plain", "text/html"}:
            decoded = _decode_base64url(data)
            if mime_type == "text/plain":
                text_parts.append(decoded)
            else:
                html_parts.append(decoded)

        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return "\n\n".join(text_parts).strip(), "\n\n".join(html_parts).strip()


def _decode_base64url(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result

