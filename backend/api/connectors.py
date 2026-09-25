from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.base import get_db
from models.user import User
from schemas.connector import ConnectorCreate, ConnectorUpdate, ConnectorRead
from auth.dependencies import get_current_user
from services import connector_service

router = APIRouter(prefix="/connectors", tags=["Connectors"])

@router.get("", response_model=List[ConnectorRead])
def list_connectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve list of registered connectors."""
    connectors = connector_service.get_connectors(db, organization_id=current_user.organization_id)
    return connectors

@router.post("", response_model=ConnectorRead, status_code=status.HTTP_201_CREATED)
def create_connector(
    connector_in: ConnectorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register a new connector."""
    if not connector_in.organization_id and current_user.organization_id:
        connector_in.organization_id = current_user.organization_id
        
    connector = connector_service.create_connector(db, connector_in)
    return connector

@router.put("/{connector_id}", response_model=ConnectorRead)
def update_connector(
    connector_id: str,
    connector_in: ConnectorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update connector details or configuration."""
    connector = connector_service.get_connector_by_id(db, connector_id)
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector with ID '{connector_id}' not found"
        )
    return connector_service.update_connector(db, connector, connector_in)

@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a registered connector."""
    connector = connector_service.get_connector_by_id(db, connector_id)
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector with ID '{connector_id}' not found"
        )
    connector_service.delete_connector(db, connector)
    return None
