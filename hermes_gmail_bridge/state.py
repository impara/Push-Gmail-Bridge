from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists state (
                    key text primary key,
                    value text not null
                );

                create table if not exists pubsub_dedupe (
                    message_id text primary key,
                    received_at text default current_timestamp
                );

                create table if not exists gmail_dedupe (
                    gmail_id text primary key,
                    thread_id text not null,
                    processed_at text default current_timestamp
                );

                create table if not exists failed_deliveries (
                    id integer primary key autoincrement,
                    gmail_id text not null,
                    payload_json text not null,
                    error text not null,
                    created_at text default current_timestamp
                );
                """
            )

    def get(self, key: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute("select value from state where key = ?", (key,)).fetchone()
            return str(row["value"]) if row else None

    def set(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert into state(key, value) values(?, ?) "
                "on conflict(key) do update set value = excluded.value",
                (key, value),
            )

    def mark_pubsub_seen(self, message_id: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                "insert or ignore into pubsub_dedupe(message_id) values(?)",
                (message_id,),
            )
            return cursor.rowcount == 1

    def mark_gmail_seen(self, gmail_id: str, thread_id: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                "insert or ignore into gmail_dedupe(gmail_id, thread_id) values(?, ?)",
                (gmail_id, thread_id),
            )
            return cursor.rowcount == 1

    def record_failed_delivery(self, gmail_id: str, payload_json: str, error: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert into failed_deliveries(gmail_id, payload_json, error) values(?, ?, ?)",
                (gmail_id, payload_json, error),
            )

