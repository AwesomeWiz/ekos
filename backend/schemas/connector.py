from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ConnectorConfigCreate(BaseModel):
    api_url: Optional[str] = None
    token: Optional[str] = None
    sync_interval: Optional[str] = "1 hour"

class ConnectorConfigRead(BaseModel):
    id: str
    connector_id: str
    api_url: Optional[str] = None
    sync_interval: Optional[str] = "1 hour"
    last_sync: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ConnectorCreate(BaseModel):
    name: str
    type: str
    organization_id: Optional[str] = None
    configuration: Optional[ConnectorConfigCreate] = None

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[ConnectorConfigCreate] = None

class ConnectorRead(BaseModel):
    id: str
    name: str
    type: str
    status: str
    organization_id: Optional[str] = None
    created_at: datetime
    configuration: Optional[ConnectorConfigRead] = None

    model_config = ConfigDict(from_attributes=True)


class ConnectorTestResponse(BaseModel):
    status: str
    connector: str
    account: Optional[str] = None
    details: Optional[str] = None

class ConnectorSyncResponse(BaseModel):
    status: str
    connector: str
    records_processed: int = 0
    documents_indexed: int = 0
    graph_nodes_updated: int = 0
    repository: Optional[str] = None
    default_branch: Optional[str] = None
    branches: Optional[int] = None
    commits: Optional[int] = None
    issues: Optional[int] = None
    synced_at: Optional[datetime] = None

# Backward compatibility aliases
GitHubTestResponse = ConnectorTestResponse
GitHubSyncResponse = ConnectorSyncResponse

