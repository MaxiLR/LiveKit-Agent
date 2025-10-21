"""Core components for PDF-based retrieval-augmented generation."""

from .openai_retriever import Hit, OpenAIRetriever

__all__ = [
    "Hit",
    "OpenAIRetriever",
]
