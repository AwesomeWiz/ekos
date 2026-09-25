import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class Connector(Base):
    __tablename__ = "connectors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    status = Column(String(50), default="active")
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="connectors")
    configuration = relationship("ConnectorConfiguration", back_populates="connector", uselist=False, cascade="all, delete-orphan")


class ConnectorConfiguration(Base):
    __tablename__ = "connector_configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id = Column(String(36), ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False, unique=True)
    api_url = Column(String(500), nullable=True)
    encrypted_token = Column(Text, nullable=True)
    sync_interval = Column(String(50), default="1 hour")
    last_sync = Column(DateTime, nullable=True)

    # Relationship
    connector = relationship("Connector", back_populates="configuration")
