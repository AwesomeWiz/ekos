"""Manual / live integration script for the Slack connector.

Usage:
    python backend/scripts/test_slack_live.py

Requires the following environment variables (or defined in backend/.env):
    SLACK_BOT_TOKEN: Bot user OAuth token (xoxb-...)
    SLACK_CHANNEL_ID: (optional) Target channel ID (e.g. C012345678)
    SLACK_API_URL: (optional) Defaults to https://slack.com/api
"""

import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from connectors.slack.connector import SlackConnector

# Load environment from root or backend .env
load_dotenv(backend_dir / ".env")
load_dotenv(backend_dir.parent / ".env")


def main():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("SLACK_CHANNEL_ID")
    base_url = os.getenv("SLACK_API_URL", "https://slack.com/api")

    if not token:
        print("=" * 60)
        print("Slack Live Integration Test - Configuration Missing")
        print("=" * 60)
        print("Please configure the following environment variables in backend/.env:")
        print("  - SLACK_BOT_TOKEN (e.g. xoxb-...)")
        print("  - SLACK_CHANNEL_ID (optional, e.g. C012345678)")
        print("  - SLACK_API_URL (optional, default: https://slack.com/api)")
        print("=" * 60)
        sys.exit(0)

    print(f"Connecting to Slack (channel: {channel_id or 'All public/private'})...")
    connector = SlackConnector(
        token=token,
        base_url=base_url,
        channel_id=channel_id,
    )

    try:
        auth_info = connector.test_connection()
        print(f"✓ Authentication successful! Connected as Bot: {auth_info.get('user')} (Team: {auth_info.get('team')})")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)

    print("Fetching and synchronizing Slack channels, users, messages, and threads...")
    try:
        normalized_records = connector.sync()
        print(f"✓ Sync complete! Normalized {len(normalized_records)} records.")
        print("\nSample Normalized Record:")
        if normalized_records:
            print(json.dumps(normalized_records[0], indent=2))
    except Exception as e:
        print(f"✗ Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
