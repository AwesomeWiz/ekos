from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class NormalizedRecord(BaseModel):
    source: str
    entity_type: str
    external_id: str
    title: str
    content: Optional[str] = ""
    author: Optional[str] = None
    project: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    status: str = "success"
    connector: str
    records_processed: int = 0
    documents_indexed: int = 0
    graph_nodes_updated: int = 0
