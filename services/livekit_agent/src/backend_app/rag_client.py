"""Client abstraction that switches between local and remote RAG backends."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Sequence

import requests
from requests import RequestException

from livekit_agent.tools import PDFRAGTool, SourceSnippet


def _bool_env(name: str, default: str = "true") -> bool:
    value = os.getenv(name, default)
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class RAGResponse:
    answer: str
    sources: List[SourceSnippet]


class RAGClient:
    """Unified interface for local PDF RAG or the remote RAG HTTP service."""

    def __init__(
        self,
        *,
        documents_dir,
        index_dir,
        embed_model: str,
        top_k: int,
    ) -> None:
        self._top_k = top_k
        self._service_url = os.getenv("RAG_SERVICE_URL")
        self._rerank_enabled = _bool_env("RAG_RERANK_ENABLED", "true")
        if self._service_url:
            self._service_url = self._service_url.rstrip("/")
            self._pdf_tool: PDFRAGTool | None = None
        else:
            self._pdf_tool = PDFRAGTool(
                documents_dir=documents_dir,
                index_dir=index_dir,
                embed_model=embed_model,
            )

    def ask(
        self,
        question: str,
        *,
        k: int | None = None,
        rerank: bool = True,
        final_m: int | None = None,
        answer_lang: str | None = None,
    ) -> RAGResponse:
        top_k = k or self._top_k
        allow_rerank = rerank and self._rerank_enabled
        if self._service_url:
            payload = {
                "question": question,
                "k": top_k,
                "rerank": allow_rerank,
                "final_m": final_m,
                "answer_lang": answer_lang,
            }
            try:
                response = requests.post(
                    f"{self._service_url}/query", json=payload, timeout=90
                )
                response.raise_for_status()
            except RequestException as exc:
                raise RuntimeError("Failed to contact RAG service") from exc
            data = response.json()
            sources = self._from_dicts(data.get("sources", []))
            return RAGResponse(answer=data.get("answer", ""), sources=sources)

        if self._pdf_tool is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Local RAG tool not initialised")

        answer, sources = self._pdf_tool.ask(
            question,
            k=top_k,
            rerank=allow_rerank,
            final_m=final_m or top_k,
            answer_lang=answer_lang,
        )
        return RAGResponse(answer=answer, sources=sources)

    def search(self, query: str, *, k: int | None = None) -> Sequence[SourceSnippet]:
        top_k = k or self._top_k
        if self._service_url:
            payload = {"query": query, "k": top_k}
            try:
                response = requests.post(
                    f"{self._service_url}/search", json=payload, timeout=60
                )
                response.raise_for_status()
            except RequestException as exc:
                raise RuntimeError("Failed to contact RAG service") from exc
            return self._from_dicts(response.json().get("sources", []))

        if self._pdf_tool is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Local RAG tool not initialised")

        return self._pdf_tool.search(query, k=top_k)

    @staticmethod
    def _from_dicts(items: Sequence[dict]) -> List[SourceSnippet]:
        sources: List[SourceSnippet] = []
        for item in items:
            sources.append(
                SourceSnippet(
                    source=item.get("source", "unknown"),
                    page=int(item.get("page", 0) or 0),
                    score=float(item.get("score", 0.0) or 0.0),
                    preview=item.get("preview", ""),
                    lang=item.get("lang", "unknown"),
                )
            )
        return sources
