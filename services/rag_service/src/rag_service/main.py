"""FastAPI application exposing the PDF RAG service."""

from __future__ import annotations

import os
import logging
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException

from .config import settings
from .models import (
    QueryRequest,
    QueryResponse,
    SearchRequest,
    SearchResponse,
    SourceResponse,
)

# Disable Hugging Face tokenizers parallel threads before worker forks.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from .service import RAGEngine, SourcePayload

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LiveKit RAG Service",
    version="0.1.0",
    summary="Provides retrieval-augmented generation utilities to multiple agents.",
)

rag_engine: RAGEngine | None = None


@app.on_event("startup")
async def load_resources() -> None:
    global rag_engine
    try:
        rag_engine = RAGEngine(
            documents_dir=settings.documents_dir,
            index_dir=settings.index_dir,
            embed_model=settings.embed_model,
            enable_rerank=settings.enable_rerank,
            rerank_model=settings.rerank_model,
        )
        logger.info(
            "RAG index loaded", extra={"documents_dir": str(settings.documents_dir)}
        )
    except FileNotFoundError as exc:  # pragma: no cover - startup guard
        logger.error("Failed to load RAG index", exc_info=exc)
        raise
    except RuntimeError as exc:  # pragma: no cover - startup guard
        logger.error("Failed to synchronise RAG index", exc_info=exc)
        raise


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _serialize_sources(sources: List[SourcePayload]) -> List[SourceResponse]:
    return [
        SourceResponse(
            source=src.source,
            page=src.page,
            score=src.score,
            lang=src.lang,
            preview=src.preview,
        )
        for src in sources
    ]


@app.post("/query", response_model=QueryResponse, tags=["rag"])
async def query_rag(request: QueryRequest) -> QueryResponse:
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not initialised")

    k = request.k or settings.default_top_k
    final_m = request.final_m or k

    try:
        answer, sources = rag_engine.ask(
            question=request.question,
            k=k,
            use_rerank=request.rerank,
            final_m=final_m,
            answer_lang=request.answer_lang,
        )
    except Exception as exc:  # pragma: no cover - protects upstream errors
        logger.exception("RAG query failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(answer=answer, sources=_serialize_sources(list(sources)))


@app.post("/search", response_model=SearchResponse, tags=["rag"])
async def search_rag(request: SearchRequest) -> SearchResponse:
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not initialised")

    k = request.k or settings.default_top_k

    try:
        sources = rag_engine.search(query=request.query, k=k)
    except Exception as exc:  # pragma: no cover - protects upstream errors
        logger.exception("RAG search failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SearchResponse(sources=_serialize_sources(list(sources)))


def run() -> None:
    """Run the FastAPI application using uvicorn."""
    uvicorn.run(
        "rag_service.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=False,
        factory=False,
    )
