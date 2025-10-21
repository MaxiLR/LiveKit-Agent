"""FastAPI application exposing the OpenAI-backed RAG service."""

from __future__ import annotations

import os
import logging
import re
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import (
    DocumentIngestResponse,
    DocumentListResponse,
    DocumentSummary,
    QueryRequest,
    QueryResponse,
    SearchRequest,
    SearchResponse,
    SourceResponse,
)

# Disable Hugging Face tokenizers parallel threads before worker forks.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from rag_core.openai_retriever import OpenAIRetriever

from .service import RAGEngine, SourcePayload

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LiveKit RAG Service",
    version="0.1.0",
    summary="Provides retrieval-augmented generation utilities to multiple agents.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins) or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine: RAGEngine | None = None

try:
    _max_size_override = os.getenv("RAG_MAX_DOCUMENT_BYTES", "").strip()
    MAX_DOCUMENT_BYTES = int(_max_size_override) if _max_size_override else 25 * 1024 * 1024
except ValueError:
    MAX_DOCUMENT_BYTES = 25 * 1024 * 1024


def _ensure_documents_dir() -> Path:
    directory = settings.documents_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


_FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(filename: str) -> str:
    name = Path(filename or "document.pdf").name
    stem = _FILENAME_SANITIZER.sub("-", Path(name).stem).strip("-_") or "document"
    suffix = Path(name).suffix.lower()
    if suffix != ".pdf":
        suffix = ".pdf"
    return f"{stem}{suffix}"


def _dedupe_filename(base: str, directory: Path) -> str:
    candidate = base
    stem = Path(base).stem
    suffix = Path(base).suffix
    counter = 1
    while (directory / candidate).exists():
        candidate = f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


@app.on_event("startup")
async def load_resources() -> None:
    global rag_engine
    try:
        retriever = OpenAIRetriever(
            vector_store_id=settings.openai_vector_store_id or None,
            vector_store_name=settings.openai_vector_store_name,
            model=settings.openai_rag_model,
            default_top_k=settings.default_top_k,
            auto_sync=settings.openai_sync_documents,
            documents_dir=settings.documents_dir,
        )
        settings.openai_vector_store_id = retriever.vector_store_id
        rag_engine = RAGEngine(retriever=retriever)
        logger.info(
            "OpenAI vector store ready",
            extra={"vector_store_id": retriever.vector_store_id},
        )
    except Exception as exc:  # pragma: no cover - startup guard
        logger.error("Failed to initialise OpenAI retrieval", exc_info=exc)
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


@app.get("/documents", response_model=DocumentListResponse, tags=["rag"])
async def list_documents() -> DocumentListResponse:
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not initialised")

    directory = _ensure_documents_dir()
    documents: List[DocumentSummary] = []
    for path in sorted(directory.rglob("*.pdf")):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        documents.append(DocumentSummary(filename=path.name, size_bytes=size))

    return DocumentListResponse(
        documents=documents,
        vector_store_id=rag_engine.vector_store_id,
    )


@app.post("/documents", response_model=DocumentIngestResponse, tags=["rag"], status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> DocumentIngestResponse:
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not initialised")

    content_type = (file.content_type or "").lower()
    if content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"PDF exceeds the maximum accepted size of {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB.",
        )

    directory = _ensure_documents_dir()
    sanitized = _sanitize_filename(file.filename or "document.pdf")
    filename = _dedupe_filename(sanitized, directory)
    target_path = directory / filename

    try:
        target_path.write_bytes(data)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist document: {exc}") from exc

    try:
        uploaded = rag_engine.ingest_document(target_path)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Document disappeared before ingestion.")
    except Exception as exc:  # pragma: no cover - best effort guard
        logger.exception("Failed to upload document %s", filename)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    summary = DocumentSummary(filename=filename, size_bytes=target_path.stat().st_size)
    return DocumentIngestResponse(
        document=summary,
        vector_store_id=rag_engine.vector_store_id,
        already_present=not uploaded,
    )


def run() -> None:
    """Run the FastAPI application using uvicorn."""
    uvicorn.run(
        "rag_service.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=False,
        factory=False,
    )
