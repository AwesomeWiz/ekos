"""Manual / live integration script for the Jira connector.

Usage:
    python backend/scripts/test_jira_live.py

Requires the following environment variables (or defined in backend/.env):
    JIRA_URL: e.g. https://your-domain.atlassian.net
    JIRA_EMAIL: e.g. user@your-company.com
    JIRA_API_TOKEN: Atlassian API token
    JIRA_PROJECT_KEY: (optional) e.g. EKOS
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
from connectors.jira.connector import JiraConnector

# Load environment from root or backend .env
load_dotenv(backend_dir / ".env")
load_dotenv(backend_dir.parent / ".env")


def main():
    base_url = os.getenv("JIRA_URL")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")
    project_key = os.getenv("JIRA_PROJECT_KEY")

    if not base_url or not token:
        print("=" * 60)
        print("Jira Live Integration Test - Configuration Missing")
        print("=" * 60)
        print("Please configure the following environment variables in backend/.env:")
        print("  - JIRA_URL (e.g. https://your-domain.atlassian.net)")
        print("  - JIRA_API_TOKEN (Atlassian API token)")
        print("  - JIRA_EMAIL (Atlassian user email for Cloud, optional for Server/PAT)")
        print("  - JIRA_PROJECT_KEY (optional, e.g. EKOS)")
        print("=" * 60)
        sys.exit(0)

    print(f"Connecting to Jira at {base_url} (project: {project_key or 'All'})...")
    connector = JiraConnector(
        base_url=base_url,
        token=token,
        email=email,
        project_key=project_key,
    )

    try:
        user_info = connector.test_connection()
        print(f"✓ Authentication successful! Connected as: {user_info.get('displayName')} ({user_info.get('emailAddress')})")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)

    print("Fetching and synchronizing Jira entities...")
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
