#!/usr/bin/env python3
from hermes_gmail_bridge.config import get_settings
from hermes_gmail_bridge.gmail_client import GmailClient


def main() -> None:
    settings = get_settings()
    client = GmailClient(settings.google_credentials_file, settings.google_token_file)
    client.service.users().getProfile(userId="me").execute()
    print(f"OAuth token written to {settings.google_token_file}")


if __name__ == "__main__":
    main()

