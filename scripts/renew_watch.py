#!/usr/bin/env python3
from hermes_gmail_bridge.config import get_settings
from hermes_gmail_bridge.gmail_client import GmailClient
from hermes_gmail_bridge.processor import LAST_HISTORY_ID
from hermes_gmail_bridge.state import StateStore


def main() -> None:
    settings = get_settings()
    if not settings.google_pubsub_topic:
        raise SystemExit("GOOGLE_PUBSUB_TOPIC is required, e.g. projects/<project-id>/topics/<topic-name>")

    gmail = GmailClient(settings.google_credentials_file, settings.google_token_file)
    state = StateStore(settings.sqlite_path)
    response = gmail.watch(settings.google_pubsub_topic, settings.label_ids)

    history_id = str(response.get("historyId", ""))
    expiration = str(response.get("expiration", ""))
    if history_id:
        state.set(LAST_HISTORY_ID, history_id)
    if expiration:
        state.set("watch_expiration_ms", expiration)

    print(f"Watch renewed for labels={settings.label_ids or ['ALL']}")
    print(f"historyId={history_id}")
    print(f"expiration_ms={expiration}")


if __name__ == "__main__":
    main()

