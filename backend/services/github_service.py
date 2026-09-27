"""Thin API adapter for the existing teammate-built GitHubConnector."""

from datetime import datetime, timezone
import logging

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from config.settings import settings
from connectors.github.connector import GitHubConnector
from models.connector import Connector
from services.indexing_service import index_github_data

logger = logging.getLogger(__name__)


def _configured_connector(connector: Connector) -> GitHubConnector:
    if connector.type.lower() != "github":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This action is available for GitHub connectors only.")
    if not (settings.GITHUB_TOKEN and settings.GITHUB_OWNER and settings.GITHUB_REPO):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Configure GITHUB_TOKEN, GITHUB_OWNER and GITHUB_REPO on the backend, then restart it.",
        )
    return GitHubConnector(settings.GITHUB_TOKEN, settings.GITHUB_OWNER, settings.GITHUB_REPO)


def _github_failure(db: Session, connector: Connector, error: Exception) -> None:
    connector.status = "error"
    db.commit()
    if isinstance(error, httpx.HTTPStatusError):
        detail = f"GitHub returned HTTP {error.response.status_code}. Check the server token and repository access."
    elif isinstance(error, httpx.RequestError):
        detail = "GitHub could not be reached. Please try again."
    else:
        detail = "GitHub returned an unexpected response. Please try again."
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from error


def test_github_connection(db: Session, connector: Connector) -> dict:
    github = _configured_connector(connector)
    try:
        account = github.test_connection()
        account_name = account["login"]
    except Exception as error:
        _github_failure(db, connector, error)
    connector.status = "connected"
    db.commit()
    return {"status": "connected", "connector": "GitHub", "account": account_name}


def sync_github_connector(db: Session, connector: Connector) -> dict:
    github = _configured_connector(connector)
    try:
        result = github.sync()
        repository = result["repository"]
        repository_name = repository["full_name"]
        default_branch = repository["default_branch"]
        branch_count = len(result["branches"])
        commit_count = len(result["commits"])
        issue_count = len(result["issues"])
    except Exception as error:
        _github_failure(db, connector, error)
    synced_at = datetime.now(timezone.utc)
    connector.status = "synced"
    if connector.configuration:
        connector.configuration.last_sync = synced_at
    db.commit()
    try:
        if not connector.organization_id:
            raise ValueError("An organization is required for knowledge indexing")
        indexing = index_github_data(result, connector.organization_id, connector.id, connector.name)
    except Exception as error:
        logger.exception("GitHub sync succeeded but indexing failed for connector %s (%s)", connector.id, type(error).__name__)
        indexing = {"status": "error", "documents_indexed": 0, "chroma_total": None,
                    "error": "GitHub synced, but knowledge indexing failed. Check the backend Chroma/model setup and retry Sync."}
    return {
        "status": "success", "connector": "GitHub", "repository": repository_name,
        "default_branch": default_branch, "branches": branch_count,
        "commits": commit_count, "issues": issue_count, "synced_at": synced_at, "indexing": indexing,
    }
