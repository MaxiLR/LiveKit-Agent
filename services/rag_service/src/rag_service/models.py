"""Request/response models exposed by the RAG HTTP API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question to answer")
    k: Optional[int] = Field(
        None, ge=1, le=12, description="Number of passages to retrieve"
    )
    rerank: bool = Field(False, description="Apply cross-encoder re-ranking if available")
    final_m: Optional[int] = Field(
        None,
        ge=1,
        le=12,
        description="Number of passages to pass to the LLM after re-ranking",
    )
    answer_lang: Optional[str] = Field(
        None, description="Force responses in a specific ISO language code"
    )


class SearchRequest(BaseModel):
    query: str = Field(..., description="Vector search query string")
    k: Optional[int] = Field(
        None, ge=1, le=20, description="Number of nearest neighbors to return"
    )


class SourceResponse(BaseModel):
    source: str
    page: int
    score: float
    lang: str
    preview: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceResponse]


class SearchResponse(BaseModel):
    sources: List[SourceResponse]
