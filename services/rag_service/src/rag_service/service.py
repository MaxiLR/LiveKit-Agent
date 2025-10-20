"""RAG orchestration logic shared by FastAPI routes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

from rag_core.pdf_indexer import Hit, PDFKnowledgeBase


@dataclass(slots=True)
class SourcePayload:
    """Serializable view of a retrieved passage."""

    source: str
    page: int
    score: float
    lang: str
    preview: str


class RAGEngine:
    """Wraps PDFKnowledgeBase and exposes higher level helpers."""

    def __init__(
        self,
        documents_dir,
        index_dir,
        embed_model: str,
        *,
        enable_rerank: bool,
        rerank_model: str,
    ) -> None:
        documents_dir = Path(documents_dir)
        index_dir = Path(index_dir)
        if not documents_dir.exists():
            raise FileNotFoundError(
                f"Documents directory not found at {documents_dir}. "
                "Create it and add at least one PDF."
            )
        index_dir.mkdir(parents=True, exist_ok=True)

        self._kb = PDFKnowledgeBase(
            documents_dir=documents_dir,
            index_dir=index_dir,
            embed_model=embed_model,
        )
        # Ensure the FAISS index is ready as part of the service startup.
        self._kb.ensure_index(show_progress=False)
        self._enable_rerank = enable_rerank
        self._rerank_model = rerank_model

    def ask(
        self,
        question: str,
        *,
        k: int,
        use_rerank: bool = False,
        final_m: int | None = None,
        answer_lang: str | None = None,
    ) -> Tuple[str, Sequence[SourcePayload]]:
        allow_rerank = use_rerank and self._enable_rerank
        answer, hits = self._kb.answer(
            question,
            k=k,
            use_rerank=allow_rerank,
            rerank_model=self._rerank_model,
            final_m=final_m or k,
            answer_lang=answer_lang,
        )
        return answer, self._to_payload(hits)

    def search(self, query: str, *, k: int) -> Sequence[SourcePayload]:
        hits = self._kb.search(query, k=k)
        return self._to_payload(hits)

    @staticmethod
    def _to_payload(hits: Sequence[Hit]) -> List[SourcePayload]:
        payload: List[SourcePayload] = []
        for hit in hits:
            payload.append(
                SourcePayload(
                    source=hit.source,
                    page=hit.page,
                    score=float(hit.score),
                    lang=hit.lang,
                    preview=hit.text[:220].replace("\n", " "),
                )
            )
        return payload
