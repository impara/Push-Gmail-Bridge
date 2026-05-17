#!/usr/bin/env python3
import asyncio
import json

from hermes_gmail_bridge.config import get_settings
from hermes_gmail_bridge.hermes import HermesClient
from hermes_gmail_bridge.state import StateStore


async def main() -> None:
    settings = get_settings()
    store = StateStore(settings.sqlite_path)
    hermes = HermesClient(str(settings.hermes_webhook_url), settings.hermes_webhook_token)

    retried = 0
    with store.connect() as conn:
        rows = conn.execute("select id, payload_json from failed_deliveries order by id").fetchall()
        for row in rows:
            await hermes.deliver(json.loads(row["payload_json"]))
            conn.execute("delete from failed_deliveries where id = ?", (row["id"],))
            retried += 1

    print(f"Retried {retried} failed Hermes deliveries")


if __name__ == "__main__":
    asyncio.run(main())

