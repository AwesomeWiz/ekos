from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.base import get_db
from models.user import User
from schemas.connector import ConnectorCreate, ConnectorUpdate, ConnectorRead, ConnectorTestResponse, ConnectorSyncResponse
from auth.dependencies import require_permission
from services import connector_service, connector_orchestration_service

router = APIRouter(prefix="/connectors", tags=["Connectors"])



@router.get("", response_model=List[ConnectorRead])
def list_connectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("connectors", "read"))
):
    """Retrieve list of registered connectors."""
    connectors = connector_service.get_connectors(db, organization_id=current_user.organization_id)
    return connectors

@router.post("", response_model=ConnectorRead, status_code=status.HTTP_201_CREATED)
def create_connector(
    connector_in: ConnectorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("connectors", "manage"))
):
    """Register a new connector."""
    connector_in.organization_id = current_user.organization_id
        
    connector = connector_service.create_connector(db, connector_in)
    return connector

@router.put("/{connector_id}", response_model=ConnectorRead)
def update_connector(
    connector_id: str,
    connector_in: ConnectorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("connectors", "manage"))
):
    """Update connector details or configuration."""
    connector = connector_service.get_connector_by_id(db, connector_id)
    if not connector or connector.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector with ID '{connector_id}' not found"
        )
    return connector_service.update_connector(db, connector, connector_in)

@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("connectors", "manage"))
):
    """Delete a registered connector."""
    connector = connector_service.get_connector_by_id(db, connector_id)
    if not connector or connector.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector with ID '{connector_id}' not found"
        )
    connector_service.delete_connector(db, connector)
    return None


def _owned_connector(db: Session, connector_id: str, current_user: User):
    connector = connector_service.get_connector_by_id(db, connector_id)
    if not connector or connector.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    return connector


@router.post("/{connector_id}/test", response_model=ConnectorTestResponse, response_model_exclude_none=True)
def test_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("connectors", "test")),
):
    """Check the configured connector through the generic connector dispatcher."""
    return connector_orchestration_service.test_connector_connection(db, _owned_connector(db, connector_id, current_user))


@router.post("/{connector_id}/sync", response_model=ConnectorSyncResponse)
def sync_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("connectors", "sync")),
):
    """Fetch, transform, and index connector data through generic ingestion orchestrator."""
    return connector_orchestration_service.sync_connector_execution(db, _owned_connector(db, connector_id, current_user))



