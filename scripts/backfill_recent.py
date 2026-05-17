#!/usr/bin/env python3
import asyncio

from hermes_gmail_bridge.config import get_settings
from hermes_gmail_bridge.gmail_client import GmailClient
from hermes_gmail_bridge.hermes import HermesClient
from hermes_gmail_bridge.processor import NotificationProcessor
from hermes_gmail_bridge.state import StateStore


async def main() -> None:
    settings = get_settings()
    state = StateStore(settings.sqlite_path)
    gmail = GmailClient(settings.google_credentials_file, settings.google_token_file)
    hermes = HermesClient(str(settings.hermes_webhook_url), settings.hermes_webhook_token)
    processor = NotificationProcessor(settings, state, gmail, hermes)

    message_ids = gmail.list_recent_message_ids(settings.recovery_query)
    for message_id in message_ids:
        await processor._process_message(message_id)
    print(f"Backfilled {len(message_ids)} recent Gmail messages using query: {settings.recovery_query}")


if __name__ == "__main__":
    asyncio.run(main())

