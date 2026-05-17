from __future__ import annotations

from fastapi import Header, HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


async def verify_pubsub_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    settings = request.app.state.settings

    if settings.pubsub_bearer_token:
        expected = f"Bearer {settings.pubsub_bearer_token}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="Invalid Pub/Sub bearer token")
        return

    if settings.pubsub_audience:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Pub/Sub OIDC token")
        token = authorization.removeprefix("Bearer ").strip()
        try:
            id_token.verify_oauth2_token(token, google_requests.Request(), settings.pubsub_audience)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid Pub/Sub OIDC token") from exc

