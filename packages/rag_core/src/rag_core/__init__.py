"""Core components for PDF-based retrieval-augmented generation."""

from .pdf_indexer import (
    DocChunk,
    Hit,
    PDFIndexer,
    PDFKnowledgeBase,
    chunk_text,
    extract_pdf_chunks,
)

__all__ = [
    "DocChunk",
    "Hit",
    "PDFIndexer",
    "PDFKnowledgeBase",
    "chunk_text",
    "extract_pdf_chunks",
]
