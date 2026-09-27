from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class NormalizedRecord(BaseModel):
    """Canonical data model for all AEKOS connectors.
    
    Provides a uniform entity structure across Jira, Confluence, Slack, and GitHub
    so downstream ingestion/storage layers do not require connector-specific logic.
    """
    source: str
    entity_type: str
    external_id: str
    title: str
    content: str
    author: Optional[str] = None
    project: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the normalized record to a plain dictionary."""
        return self.model_dump()
