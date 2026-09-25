from typing import List, Optional
from sqlalchemy.orm import Session
from models.connector import Connector, ConnectorConfiguration
from schemas.connector import ConnectorCreate, ConnectorUpdate

def get_connectors(db: Session, organization_id: Optional[str] = None) -> List[Connector]:
    """Retrieve connectors from database."""
    query = db.query(Connector)
    if organization_id:
        query = query.filter(Connector.organization_id == organization_id)
    return query.all()

def get_connector_by_id(db: Session, connector_id: str) -> Optional[Connector]:
    """Retrieve a single connector by UUID."""
    return db.query(Connector).filter(Connector.id == connector_id).first()

def create_connector(db: Session, connector_in: ConnectorCreate) -> Connector:
    """Create a new connector along with its initial configuration."""
    connector = Connector(
        name=connector_in.name,
        type=connector_in.type,
        status="active",
        organization_id=connector_in.organization_id
    )
    db.add(connector)
    db.flush()  # Generate connector.id

    if connector_in.configuration:
        config = ConnectorConfiguration(
            connector_id=connector.id,
            api_url=connector_in.configuration.api_url,
            encrypted_token=connector_in.configuration.token,  # In prototype, stored as placeholder token
            sync_interval=connector_in.configuration.sync_interval or "1 hour"
        )
        db.add(config)

    db.commit()
    db.refresh(connector)
    return connector

def update_connector(db: Session, connector: Connector, connector_in: ConnectorUpdate) -> Connector:
    """Update existing connector metadata and configuration."""
    if connector_in.name is not None:
        connector.name = connector_in.name
    if connector_in.status is not None:
        connector.status = connector_in.status

    if connector_in.configuration:
        if connector.configuration:
            if connector_in.configuration.api_url is not None:
                connector.configuration.api_url = connector_in.configuration.api_url
            if connector_in.configuration.token is not None:
                connector.configuration.encrypted_token = connector_in.configuration.token
            if connector_in.configuration.sync_interval is not None:
                connector.configuration.sync_interval = connector_in.configuration.sync_interval
        else:
            config = ConnectorConfiguration(
                connector_id=connector.id,
                api_url=connector_in.configuration.api_url,
                encrypted_token=connector_in.configuration.token,
                sync_interval=connector_in.configuration.sync_interval or "1 hour"
            )
            db.add(config)

    db.commit()
    db.refresh(connector)
    return connector

def delete_connector(db: Session, connector: Connector) -> None:
    """Delete a connector from the database."""
    db.delete(connector)
    db.commit()
