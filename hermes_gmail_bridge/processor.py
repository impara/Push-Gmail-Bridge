from __future__ import annotations

from googleapiclient.errors import HttpError

from .config import Settings
from .gmail_client import GmailClient, GmailHistoryExpired
from .hermes import HermesClient, build_contact_inbox_payload, payload_to_json
from .models import PubSubNotification
from .state import StateStore


LAST_HISTORY_ID = "last_history_id"


class NotificationProcessor:
    def __init__(
        self,
        settings: Settings,
        state: StateStore,
        gmail: GmailClient,
        hermes: HermesClient,
    ):
        self.settings = settings
        self.state = state
        self.gmail = gmail
        self.hermes = hermes

    async def process(self, notification: PubSubNotification) -> None:
        if not self.state.mark_pubsub_seen(notification.pubsub_message_id):
            return

        start_history_id = self.state.get(LAST_HISTORY_ID)
        if not start_history_id:
            self.state.set(LAST_HISTORY_ID, notification.history_id)
            return

        try:
            message_ids, latest_history_id = self.gmail.list_history(
                start_history_id=start_history_id,
                max_results=self.settings.max_history_results,
            )
        except GmailHistoryExpired:
            message_ids = self.gmail.list_recent_message_ids(self.settings.recovery_query)
            latest_history_id = notification.history_id

        for message_id in message_ids:
            await self._process_message(message_id)

        if latest_history_id:
            self.state.set(LAST_HISTORY_ID, latest_history_id)
        else:
            self.state.set(LAST_HISTORY_ID, notification.history_id)

    async def _process_message(self, message_id: str) -> None:
        try:
            message = self.gmail.get_message(message_id)
        except HttpError:
            raise

        if not self.state.mark_gmail_seen(message.gmail_id, message.thread_id):
            return

        payload = build_contact_inbox_payload(
            message=message,
            public_inbox_address=self.settings.public_inbox_address,
            gmail_account=self.settings.gmail_account,
        )

        try:
            await self.hermes.deliver(payload)
        except Exception as exc:
            self.state.record_failed_delivery(message.gmail_id, payload_to_json(payload), str(exc))
            raise

