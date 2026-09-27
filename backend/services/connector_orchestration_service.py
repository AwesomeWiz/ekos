"""Generic connector orchestration service for testing, syncing, and ingesting records."""

from datetime import datetime, timezone
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from connectors.registry import registry, UnrecognizedConnectorTypeError
from models.connector import Connector
from schemas.connector import ConnectorTestResponse, ConnectorSyncResponse
from schemas.ingestion import NormalizedRecord
from services.ingestion_service import IngestionService
from services import github_service

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

    instance = _instantiate_registered_connector(connector)
    try:
        account_info = instance.test_connection()
        account_name = account_info.get("login") if isinstance(account_info, dict) else str(account_info)
    except Exception as error:
        connector.status = "error"
        db.commit()
        if isinstance(error, HTTPException):
            raise error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{connector.name} test connection failed: {str(error)}",
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
        )

    instance = _instantiate_registered_connector(connector)
    try:
        raw_records = instance.sync()
    except Exception as error:
        connector.status = "error"
        db.commit()
        if isinstance(error, HTTPException):
            raise error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{connector.name} sync failed: {str(error)}",
        ) from error

    normalized_records = []
    if isinstance(raw_records, list):
        for item in raw_records:
            if isinstance(item, NormalizedRecord):
                normalized_records.append(item)
            elif isinstance(item, dict):
                try:
                    normalized_records.append(NormalizedRecord(**item))
                except Exception:
                    pass

    ingestion_stats = _ingestion_service.process_records(connector.name, normalized_records)

    synced_at = datetime.now(timezone.utc)
    connector.status = "synced"
    if connector.configuration:
        connector.configuration.last_sync = synced_at
    db.commit()

    return ConnectorSyncResponse(
        status="success",
        connector=connector.name,
        records_processed=ingestion_stats.records_processed,
        documents_indexed=ingestion_stats.documents_indexed,
        graph_nodes_updated=ingestion_stats.graph_nodes_updated,
        synced_at=synced_at,
    )
