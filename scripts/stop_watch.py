#!/usr/bin/env python3
from hermes_gmail_bridge.config import get_settings
from hermes_gmail_bridge.gmail_client import GmailClient


def main() -> None:
    settings = get_settings()
    GmailClient(settings.google_credentials_file, settings.google_token_file).stop_watch()
    print("Gmail watch stopped")


if __name__ == "__main__":
    main()

