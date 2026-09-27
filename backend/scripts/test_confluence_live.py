"""Manual / live integration script for the Confluence connector.

Usage:
    python backend/scripts/test_confluence_live.py

Requires the following environment variables (or defined in backend/.env):
    CONFLUENCE_URL: e.g. https://your-domain.atlassian.net/wiki
    CONFLUENCE_EMAIL: e.g. user@your-company.com
    CONFLUENCE_API_TOKEN: Atlassian API token
    CONFLUENCE_SPACE_KEY: (optional) e.g. EKOS
"""

import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from connectors.confluence.connector import ConfluenceConnector

# Load environment from root or backend .env
load_dotenv(backend_dir / ".env")
load_dotenv(backend_dir.parent / ".env")


def main():
    base_url = os.getenv("CONFLUENCE_URL")
    email = os.getenv("CONFLUENCE_EMAIL")
    token = os.getenv("CONFLUENCE_API_TOKEN")
    space_key = os.getenv("CONFLUENCE_SPACE_KEY")

    if not base_url or not token:
        print("=" * 60)
        print("Confluence Live Integration Test - Configuration Missing")
        print("=" * 60)
        print("Please configure the following environment variables in backend/.env:")
        print("  - CONFLUENCE_URL (e.g. https://your-domain.atlassian.net/wiki)")
        print("  - CONFLUENCE_API_TOKEN (Atlassian API token)")
        print("  - CONFLUENCE_EMAIL (Atlassian user email for Cloud, optional for Server/PAT)")
        print("  - CONFLUENCE_SPACE_KEY (optional, e.g. EKOS)")
        print("=" * 60)
        sys.exit(0)

    print(f"Connecting to Confluence at {base_url} (space: {space_key or 'All'})...")
    connector = ConfluenceConnector(
        base_url=base_url,
        token=token,
        email=email,
        space_key=space_key,
    )

    try:
        user_info = connector.test_connection()
        user_name = user_info.get("displayName") or user_info.get("publicName") or "Authenticated User"
        print(f"✓ Authentication successful! Connected as: {user_name}")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)

    print("Fetching and synchronizing Confluence spaces and pages...")
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
