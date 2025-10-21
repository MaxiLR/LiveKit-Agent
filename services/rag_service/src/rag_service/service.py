"""RAG orchestration logic shared by FastAPI routes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

from rag_core.openai_retriever import Hit, OpenAIRetriever


@dataclass(slots=True)
class SourcePayload:
    """Serializable view of a retrieved passage."""

    source: str
    page: int
    score: float
    lang: str
    preview: str


class RAGEngine:
    """Thin wrapper around the shared OpenAI retriever utility."""

    def __init__(
        self,
        retriever: OpenAIRetriever,
    ) -> None:
        self._retriever = retriever

    def ask(
        self,
        question: str,
        *,
        k: int,
        use_rerank: bool = False,
        final_m: int | None = None,
        answer_lang: str | None = None,
    ) -> Tuple[str, Sequence[SourcePayload]]:
        answer, hits = self._retriever.ask(
            question,
            k=final_m or k,
            answer_lang=answer_lang,
            metadata={"requested_top_k": str(k)},
        )
        return answer, self._to_payload(hits)

    def search(self, query: str, *, k: int) -> Sequence[SourcePayload]:
        hits = self._retriever.search(query, k=k)
        return self._to_payload(hits)

    def ingest_document(self, file_path: Path) -> bool:
        return self._retriever.ingest_document(file_path)

    @property
    def vector_store_id(self) -> str:
        return self._retriever.vector_store_id

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
