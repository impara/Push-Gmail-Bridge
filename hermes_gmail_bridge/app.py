from __future__ import annotations

import logging

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response

from .auth import verify_pubsub_auth
from .config import Settings, get_settings
from .gmail_client import GmailClient
from .hermes import HermesClient
from .processor import NotificationProcessor
from .pubsub import PubSubPayloadError, parse_pubsub_push
from .state import StateStore

logger = logging.getLogger(__name__)


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

    return app


async def _process_safely(processor: NotificationProcessor, notification) -> None:
    try:
        await processor.process(notification)
    except Exception:
        logger.exception("Failed to process Gmail notification history_id=%s", notification.history_id)


app = create_app()

