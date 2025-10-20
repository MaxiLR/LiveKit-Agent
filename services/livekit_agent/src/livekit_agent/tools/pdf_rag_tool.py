"""High level tool that exposes the PDF knowledge base to LiveKit agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from livekit_agent.rag import Hit, PDFKnowledgeBase


@dataclass
class SourceSnippet:
    source: str
    page: int
    score: float
    preview: str
    lang: str


class PDFRAGTool:
    """Wraps PDFKnowledgeBase with convenience helpers for function calling."""

    def __init__(
        self,
        documents_dir: Path,
        index_dir: Path,
        embed_model: str = "intfloat/multilingual-e5-base",
        chunk_size: int = 900,
        overlap: int = 150,
    ) -> None:
        self._kb = PDFKnowledgeBase(
            documents_dir=documents_dir,
            index_dir=index_dir,
            embed_model=embed_model,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        # Eagerly build or refresh the index so the agent is ready to answer.
        self._kb.ensure_index(show_progress=False)

    def ask(
        self,
        question: str,
        k: int = 6,
        rerank: bool = False,
        rerank_model: str = "BAAI/bge-reranker-v2-m3",
        final_m: int = 6,
        answer_lang: str | None = None,
    ) -> tuple[str, List[SourceSnippet]]:
        answer, hits = self._kb.answer(
            question,
            k=k,
            use_rerank=rerank,
            rerank_model=rerank_model,
            final_m=final_m,
            answer_lang=answer_lang,
        )
        return answer, self._prepare_sources(hits)

    def search(self, query: str, k: int = 6) -> List[SourceSnippet]:
        hits = self._kb.search(query, k=k)
        return self._prepare_sources(hits)

    def _prepare_sources(self, hits: Sequence[Hit]) -> List[SourceSnippet]:
        snippets: List[SourceSnippet] = []
        for hit in hits:
            snippets.append(
                SourceSnippet(
                    source=hit.source,
                    page=hit.page,
                    score=hit.score,
                    lang=hit.lang,
                    preview=hit.text[:180].replace("\n", " "),
                )
            )
        return snippets

