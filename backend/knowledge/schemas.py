from dataclasses import dataclass, field
from typing import Any


@dataclass
class EntityRecord:
    id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipRecord:
    source_id: str
    source_type: str
    relationship: str
    target_id: str
    target_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentRecord:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)