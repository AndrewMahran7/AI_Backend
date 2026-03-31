"""Pydantic schemas for the chat / query endpoint."""

from pydantic import BaseModel, Field


class ChatSource(BaseModel):
    """A single source record referenced in the answer."""

    record_id: str
    title: str


class ChatRequest(BaseModel):
    """Request body for ``POST /chat``."""

    query: str = Field(..., min_length=1, max_length=2000, description="Natural-language question")


class ChatResponse(BaseModel):
    """Response returned by ``POST /chat``."""

    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str = ""
    query_type: str = Field(default="fact", description="Classified query type (fact, summary, compare, list)")
    iterations: int = Field(default=1, description="Number of retrieval iterations used")
    used_agentic_search: bool = Field(default=False, description="Whether the model triggered additional retrieval")

