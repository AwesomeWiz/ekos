from typing import Literal

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    type: Literal["User", "Commit", "Repository", "Issue"]
    description: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
