"""Generic connector orchestration service for testing, syncing, and ingesting records."""

from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from connectors.registry import registry, UnrecognizedConnectorTypeError
from models.connector import Connector
from schemas.connector import ConnectorTestResponse, ConnectorSyncResponse
from schemas.ingestion import NormalizedRecord
from services.ingestion_service import IngestionService
from services import github_service
from config.settings import settings
from services.normalized_ingestion import ingest_connector_records

_ingestion_service = IngestionService()


def _instantiate_registered_connector(connector: Connector):
    try:
        connector_cls = registry.get_connector_class(connector.type)
    except UnrecognizedConnectorTypeError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )

    token = connector.configuration.encrypted_token if connector.configuration else ""
    api_url = connector.configuration.api_url if connector.configuration else ""
    connector_type = connector.type.strip().lower()
    if connector_type in {"jira", "confluence", "slack"}:
        prefix = connector_type.upper()
        token = token or getattr(settings, f"{prefix}_BOT_TOKEN" if connector_type == "slack" else f"{prefix}_API_TOKEN")
        base_url = api_url or getattr(settings, f"{prefix}_API_URL" if connector_type == "slack" else f"{prefix}_URL")
        if not token or not base_url:
            raise HTTPException(status_code=409, detail=f"Configure {connector_type} credentials and API URL on the backend first.")
        kwargs = {"token": token, "base_url": base_url}
        if connector_type == "slack":
            kwargs["channel_id"] = settings.SLACK_CHANNEL_ID or None
        else:
            kwargs["email"] = getattr(settings, f"{prefix}_EMAIL") or None
            key = "project_key" if connector_type == "jira" else "space_key"
            kwargs[key] = getattr(settings, f"{prefix}_{key.upper()}") or None
        return connector_cls(**kwargs)
    try:
        return connector_cls(token=token, api_url=api_url)
    except TypeError:
        return connector_cls()


def test_connector_connection(db: Session, connector: Connector) -> ConnectorTestResponse:
    """Orchestrate connector test connection generically."""
    if connector.type.lower() == "github":
        result = github_service.test_github_connection(db, connector)
        if isinstance(result, dict):
            return ConnectorTestResponse(**result)
        return result

    try:
        instance = _instantiate_registered_connector(connector)
        account_info = instance.test_connection()
        account_name = account_info.get("login") if isinstance(account_info, dict) else str(account_info)
    except Exception as error:
        connector.status = "not_configured" if isinstance(error, HTTPException) and error.status_code == 409 else "error"
        db.commit()
        if isinstance(error, HTTPException):
            raise error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{connector.name} connection test failed. Check backend credentials, permissions, and connectivity.",
        ) from error

    connector.status = "connected"
    db.commit()
    return ConnectorTestResponse(status="connected", connector=connector.name, account=account_name)


def sync_connector_execution(db: Session, connector: Connector) -> ConnectorSyncResponse:
    """Orchestrate connector data fetching, entity normalization, and ingestion."""
    if connector.type.lower() == "github":
        result = github_service.sync_github_connector(db, connector)
        if isinstance(result, dict):
            res_dict = result
        else:
            res_dict = result.model_dump()

        # Build normalized records from GitHub sync output for IngestionService
        normalized_records = []
        repo_name = res_dict.get("repository")
        if repo_name:
            normalized_records.append(NormalizedRecord(
                source="github",
                entity_type="Repository",
                external_id=repo_name,
                title=repo_name,
                project=repo_name,
            ))

        ingestion_stats = _ingestion_service.process_records(connector.name, normalized_records)

        return ConnectorSyncResponse(
            status="success",
            connector=connector.name,
            records_processed=ingestion_stats.records_processed,
            documents_indexed=ingestion_stats.documents_indexed,
            graph_nodes_updated=ingestion_stats.graph_nodes_updated,
            repository=res_dict.get("repository"),
            default_branch=res_dict.get("default_branch"),
            branches=res_dict.get("branches"),
            commits=res_dict.get("commits"),
            issues=res_dict.get("issues"),
            synced_at=res_dict.get("synced_at") or datetime.now(timezone.utc),
            indexing=res_dict.get("indexing"),
        )

    try:
        instance = _instantiate_registered_connector(connector)
        raw_records = instance.sync()
    except Exception as error:
        connector.status = "not_configured" if isinstance(error, HTTPException) and error.status_code == 409 else "error"
        db.commit()
        if isinstance(error, HTTPException):
            raise error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{connector.name} sync failed. Check backend credentials, permissions, and connectivity.",
        ) from error

    try:
        ingestion_stats = ingest_connector_records(connector, raw_records)
    except Exception as error:
        connector.status = "error"
        db.commit()
        raise HTTPException(status_code=503, detail="Connector data was fetched, but knowledge ingestion failed. Check backend storage/model setup and retry Sync.") from error

    synced_at = datetime.now(timezone.utc)
    connector.status = "synced"
    if connector.configuration:
        connector.configuration.last_sync = synced_at
    db.commit()

    return ConnectorSyncResponse(
        status="success",
        connector=connector.name,
        **ingestion_stats,
        synced_at=synced_at,
    )
