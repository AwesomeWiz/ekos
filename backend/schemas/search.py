from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    document_id: str
    text: str
    metadata: dict[str, str | int | float | bool]
    distance: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    document_count: int


class SearchStatus(BaseModel):
    collection: str
    document_count: int
    embedding_model: str
