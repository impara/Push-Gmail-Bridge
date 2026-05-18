# Hermes Gmail Bridge

Tiny push adapter for the Hermès contact inbox.

```text
Gmail watch() -> Pub/Sub -> /pubsub/gmail -> gmail.history.list -> Hermes /webhooks/contact-inbox
```

The cloud setup follows the same pattern as the Dev.to Gmail bridge, `sangnandar/Realtime-Gmail-Listener`, and Letta's `gmail-pubsub.md`: let Gmail push a cheap notification to Pub/Sub, then let our webhook fetch the full message from Gmail and forward a clean payload to the agent.

## What This Does

- Receives Gmail Pub/Sub push notifications.
- Dedupes Pub/Sub pushes and Gmail message IDs in SQLite.
- Uses `gmail.users.history.list` to discover new messages.
- Fetches full Gmail messages with `messages.get`.
- Posts normalized JSON to Hermès:

```text
POST /webhooks/contact-inbox
```

It deliberately does not classify, route, or decide what the agent should do. Hermès owns that.

The bridge also exposes a small authenticated local outbound helper:

```text
POST /outbound/reply
```

Hermès can call this after approval to send a Gmail API reply in the original thread.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

If your system Python has an older `pip`/`setuptools`, use a virtualenv as shown above. Without a virtualenv, editable installs can fall back to legacy `setup.py develop` behavior and fail on system package permissions.

Put your Google OAuth client file at:

```text
secrets/google-oauth-client.json
```

Then authorize the dedicated Gmail account:

```bash
python scripts/setup_gmail_oauth.py
```

## Google Cloud Plumbing

Create a Pub/Sub topic:

```text
projects/YOUR_PROJECT_ID/topics/hermes-contact-inbox
```

Grant Gmail permission to publish:

```bash
gcloud pubsub topics add-iam-policy-binding hermes-contact-inbox \
  --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
  --role=roles/pubsub.publisher
```

Create a push subscription to your public bridge URL:

```text
https://YOUR-BRIDGE-HOST/pubsub/gmail
```

For a fast first deploy, set `PUBSUB_BEARER_TOKEN` and configure the push subscription to include:

```text
Authorization: Bearer <token>
```

For production, configure Pub/Sub push OIDC and set `PUBSUB_AUDIENCE` to the exact audience you configure for the subscription.

## Run Locally

```bash
uvicorn hermes_gmail_bridge.app:app --host 0.0.0.0 --port 8090
```

Expose it with Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:8090
```

Set the Pub/Sub push endpoint to:

```text
https://YOUR-TUNNEL-HOST/pubsub/gmail
```

## Start Or Renew Gmail Watch

Gmail watches expire, so renew daily.

```bash
python scripts/renew_watch.py
```

This stores the returned `historyId` as the starting cursor in SQLite.

## Hermès Payload

The bridge sends:

```json
{
  "source": "gmail",
  "inbox": "contact@example.com",
  "gmail_account": "agent-inbox@gmail.com",
  "message_id": "gmail-message-id",
  "rfc822_message_id": "<message@example>",
  "thread_id": "gmail-thread-id",
  "history_id": "12345",
  "from": "Sender <sender@example.com>",
  "to": ["contact@example.com"],
  "cc": [],
  "subject": "Hello",
  "received_at": "2026-05-17T12:00:00+00:00",
  "text": "Plain text body",
  "html": "<p>HTML body</p>",
  "headers": {
    "message_id": "<message@example>",
    "in_reply_to": "",
    "references": "",
    "reply_to": ""
  },
  "raw": {
    "snippet": "Gmail snippet",
    "label_ids": ["INBOX"]
  }
}
```

## Recovery

If the Gmail history cursor expires, the bridge falls back to `RECOVERY_QUERY`, defaulting to:

```text
newer_than:3d
```

You can also manually backfill:

```bash
python scripts/backfill_recent.py
```

Failed Hermès deliveries are stored in SQLite and can be retried:

```bash
python scripts/retry_failed_deliveries.py
```

## Outbound Replies

Configure a local-only secret:

```env
HERMES_OUTBOUND_TOKEN=use-a-long-random-secret
```

Hermès can then call the bridge:

```bash
curl -X POST http://127.0.0.1:8090/outbound/reply \
  -H "Authorization: Bearer use-a-long-random-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "original_message_id": "gmail-message-id",
    "text": "Hello,\n\nThanks for reaching out.\n\nBest,"
  }'
```

The bridge fetches the original Gmail message, preserves `threadId`, `In-Reply-To`, and `References`, and sends from `PUBLIC_INBOX_ADDRESS`. That address must already be configured as a Gmail send-as alias.

The OAuth token must include:

```text
https://www.googleapis.com/auth/gmail.send
```

If you added this scope after authorizing, delete `secrets/google-token.json` and run:

```bash
python scripts/setup_gmail_oauth.py
```
