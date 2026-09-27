from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be empty.")
        return value


class ChatSource(BaseModel):
    title: str | None = None
    source: str | None = None
    connector: str | None = None
    entity_type: str | None = None
    url: str | None = None
    repository: str | None = None
    snippet: str


class GraphRelationship(BaseModel):
    source: str
    relationship: str
    target: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
    graph_context: list[GraphRelationship] = Field(default_factory=list)
