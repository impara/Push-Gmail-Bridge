from __future__ import annotations

import logging

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .auth import verify_pubsub_auth
from .config import Settings, get_settings
from .gmail_client import GmailClient
from .hermes import HermesClient
from .processor import NotificationProcessor
from .pubsub import PubSubPayloadError, parse_pubsub_push
from .state import StateStore

logger = logging.getLogger(__name__)


class ReplyRequest(BaseModel):
    original_message_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    html: str = ""
    to: list[str] | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Hermes Gmail Bridge")
    app.state.settings = settings
    app.state.store = StateStore(settings.sqlite_path)
    app.state.gmail = GmailClient(settings.google_credentials_file, settings.google_token_file)
    app.state.hermes = HermesClient(
        webhook_url=str(settings.hermes_webhook_url),
        token=settings.hermes_webhook_token,
        timeout_seconds=settings.hermes_timeout_seconds,
    )
    app.state.processor = NotificationProcessor(
        settings=settings,
        state=app.state.store,
        gmail=app.state.gmail,
        hermes=app.state.hermes,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/pubsub/gmail", dependencies=[Depends(verify_pubsub_auth)])
    async def receive_gmail_push(request: Request, background_tasks: BackgroundTasks) -> Response:
        try:
            payload = await request.json()
            notification = parse_pubsub_push(payload)
        except PubSubPayloadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        background_tasks.add_task(_process_safely, request.app.state.processor, notification)
        return Response(status_code=204)

    @app.post("/outbound/reply")
    async def send_reply(
        reply: ReplyRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, str]:
        settings = request.app.state.settings
        if not settings.hermes_outbound_token:
            raise HTTPException(status_code=503, detail="Outbound token is not configured")

        expected = f"Bearer {settings.hermes_outbound_token}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="Invalid outbound token")

        sent = request.app.state.gmail.send_reply(
            original_message_id=reply.original_message_id,
            from_addr=settings.public_inbox_address,
            text=reply.text,
            html=reply.html,
            to_addrs=reply.to,
        )
        return {
            "status": "sent",
            "message_id": str(sent.get("id", "")),
            "thread_id": str(sent.get("threadId", "")),
        }

    return app


async def _process_safely(processor: NotificationProcessor, notification) -> None:
    try:
        await processor.process(notification)
    except Exception:
        logger.exception("Failed to process Gmail notification history_id=%s", notification.history_id)


app = create_app()
