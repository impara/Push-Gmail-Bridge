# Google Setup Checklist

This checklist covers only the Google-side setup needed for the Hermès Gmail bridge.

Target flow:

```text
agent-inbox@gmail.com
  -> Gmail watch()
  -> Google Pub/Sub topic
  -> Pub/Sub push subscription
  -> https://gmail-bridge.example.com/pubsub/gmail
```

## 1. Choose Or Create A Google Cloud Project

Use a project dedicated to Hermès/agent infrastructure if possible.

Record:

```text
GOOGLE_CLOUD_PROJECT_ID=
```

## 2. Enable APIs

In Google Cloud Console, enable:

- Gmail API
- Pub/Sub API

Console path:

```text
Google Cloud Console -> APIs & Services -> Library
```

## 3. Configure OAuth Consent Screen

Console path:

```text
APIs & Services -> OAuth consent screen
```

For a personal/dedicated Gmail account, an external app in testing mode is usually fine.

Add yourself as a test user:

```text
agent-inbox@gmail.com
```

Required scopes:

```text
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.send
```

The bridge uses `gmail.modify` because Gmail watch/history integrations commonly require mailbox metadata access. It uses `gmail.send` only for the optional approved-reply endpoint that lets Hermès send a reply after approval.

## 4. Create OAuth Client

Console path:

```text
APIs & Services -> Credentials -> Create Credentials -> OAuth client ID
```

Choose:

```text
Application type: Desktop app
Name: Hermes Gmail Bridge
```

Download the JSON file and place it on the bridge server as:

```text
secrets/google-oauth-client.json
```

Set in `.env`:

```env
GOOGLE_CREDENTIALS_FILE=secrets/google-oauth-client.json
GOOGLE_TOKEN_FILE=secrets/google-token.json
```

## 5. Authorize The Gmail Account

On the bridge machine, run:

```bash
python scripts/setup_gmail_oauth.py
```

Log in as:

```text
agent-inbox@gmail.com
```

This creates:

```text
secrets/google-token.json
```

Keep both files private. Do not commit them.

If you add or change scopes later, delete `secrets/google-token.json` and run the OAuth setup script again.

## 6. Create Pub/Sub Topic

Console path:

```text
Pub/Sub -> Topics -> Create topic
```

Suggested topic ID:

```text
hermes-contact-inbox
```

Full topic name:

```text
projects/YOUR_PROJECT_ID/topics/hermes-contact-inbox
```

Set in `.env`:

```env
GOOGLE_PUBSUB_TOPIC=projects/YOUR_PROJECT_ID/topics/hermes-contact-inbox
```

## 7. Allow Gmail To Publish To The Topic

Gmail publishes push notifications as this Google-managed service account:

```text
gmail-api-push@system.gserviceaccount.com
```

Grant it:

```text
Pub/Sub Publisher
```

CLI option:

```bash
gcloud pubsub topics add-iam-policy-binding hermes-contact-inbox \
  --project=YOUR_PROJECT_ID \
  --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
  --role=roles/pubsub.publisher
```

Console option:

```text
Pub/Sub -> Topics -> hermes-contact-inbox -> Permissions
```

Add principal:

```text
gmail-api-push@system.gserviceaccount.com
```

Role:

```text
Pub/Sub Publisher
```

## 8. Create Pub/Sub Push Subscription

Console path:

```text
Pub/Sub -> Subscriptions -> Create subscription
```

Suggested subscription ID:

```text
hermes-contact-inbox-push
```

Topic:

```text
hermes-contact-inbox
```

Delivery type:

```text
Push
```

Endpoint:

```text
https://gmail-bridge.example.com/pubsub/gmail
```

Ack deadline:

```text
10 seconds
```

The bridge returns `204` quickly and processes the Gmail rehydration in the background.

## 9. Configure Pub/Sub Push Authentication

For the simplest MVP setup, leave push authentication disabled in the Pub/Sub subscription UI.

Set on the bridge:

```env
PUBSUB_BEARER_TOKEN=
PUBSUB_AUDIENCE=
```

This makes the bridge accept the normal Pub/Sub push envelope without checking a Google OIDC token. The endpoint URL is still public, so use this for initial testing only.

Do not enable payload unwrapping. The bridge expects the standard Pub/Sub JSON envelope:

```json
{
  "message": {
    "messageId": "...",
    "data": "..."
  }
}
```

### Later Upgrade: OIDC Push Auth

For a more production-ready Google-native setup:

1. Create or choose a service account for Pub/Sub push.
2. Configure the push subscription to attach an OIDC token.
3. Set the audience to your endpoint URL.

Audience:

```text
https://gmail-bridge.example.com/pubsub/gmail
```

Set on the bridge:

```env
PUBSUB_AUDIENCE=https://gmail-bridge.example.com/pubsub/gmail
```

Leave `PUBSUB_BEARER_TOKEN` empty when using OIDC.

## 10. Start Gmail Watch

After the bridge is deployed and reachable, run:

```bash
python scripts/renew_watch.py
```

This calls Gmail `users.watch()` and stores the returned `historyId`.

Expected output includes:

```text
historyId=...
expiration_ms=...
```

## 11. Schedule Watch Renewal

Gmail watches expire. Renew daily.

Use cron, systemd timer, or your deployment scheduler.

Example cron:

```cron
0 3 * * * cd /path/to/Push-Gmail-Bridge && . .venv/bin/activate && python scripts/renew_watch.py
```

## 12. Test End To End

Send an email to:

```text
contact@example.com
```

Confirm:

- Cloudflare Email Routing forwards it to `agent-inbox@gmail.com`.
- Gmail emits a Pub/Sub notification.
- Pub/Sub push receives HTTP `204`.
- Bridge logs show Gmail rehydration.
- Hermès receives `POST /webhooks/contact-inbox`.

## 13. Keep These Values Handy

```env
PUBLIC_INBOX_ADDRESS=contact@example.com
GMAIL_ACCOUNT=agent-inbox@gmail.com
GOOGLE_CREDENTIALS_FILE=secrets/google-oauth-client.json
GOOGLE_TOKEN_FILE=secrets/google-token.json
GOOGLE_PUBSUB_TOPIC=projects/YOUR_PROJECT_ID/topics/hermes-contact-inbox
GMAIL_LABEL_IDS=INBOX
HERMES_WEBHOOK_URL=http://localhost:YOUR_HERMES_PORT/webhooks/contact-inbox
HERMES_OUTBOUND_TOKEN=YOUR_LONG_RANDOM_LOCAL_SECRET
PUBSUB_BEARER_TOKEN=
PUBSUB_AUDIENCE=
```
