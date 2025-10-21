"""Utilities for working with OpenAI's hosted retrieval/vector store APIs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Hit:
    """Represents a retrieved passage with optional citation metadata."""

    score: float
    text: str
    source: str
    page: int
    lang: str = "unknown"
    file_id: Optional[str] = None


class OpenAIFileCache:
    """Caches OpenAI file metadata to avoid redundant API calls."""

    def __init__(self, client: OpenAI) -> None:
        self._client = client
        self._cache: Dict[str, str] = {}

    def filename(self, file_id: str) -> str:
        if file_id in self._cache:
            return self._cache[file_id]
        response = self._client.files.retrieve(file_id)
        name = getattr(response, "filename", file_id)
        self._cache[file_id] = name
        return name


class OpenAIRetriever:
    """Thin wrapper around OpenAI Responses + vector store APIs."""

    def __init__(
        self,
        *,
        vector_store_id: Optional[str] = None,
        vector_store_name: Optional[str] = None,
        model: str = "gpt-4.1-mini",
        client: Optional[OpenAI] = None,
        default_top_k: int = 6,
        auto_sync: bool = False,
        documents_dir: Optional[Path] = None,
    ) -> None:
        self.client = client or OpenAI()
        self.model = model
        self.default_top_k = default_top_k
        self._file_cache = OpenAIFileCache(self.client)
        self.vector_store_id = (
            vector_store_id
            if vector_store_id
            else self._ensure_vector_store(vector_store_name or "livekit-agent-rag")
        )

        if auto_sync and documents_dir:
            self.sync_documents(documents_dir)

    # ---------------------------------------------------------------------#
    # Document ingestion helpers                                           #
    # ---------------------------------------------------------------------#
    def sync_documents(self, documents_dir: Path) -> None:
        """Upload any files from documents_dir that are not yet in the store."""
        documents_dir = Path(documents_dir)
        if not documents_dir.exists():
            logger.warning(
                "Documents directory %s does not exist; skipping vector store sync.",
                documents_dir,
            )
            return

        existing = self._existing_filenames()
        files = sorted(path for path in documents_dir.glob("**/*") if path.is_file())
        to_upload: List[Path] = []
        for file_path in files:
            if file_path.name.startswith("."):
                continue
            try:
                if file_path.stat().st_size == 0:
                    logger.debug("Skipping empty file %s.", file_path)
                    continue
            except OSError:
                logger.debug("Skipping unreadable file %s.", file_path)
                continue
            if file_path.name in existing:
                continue
            to_upload.append(file_path)
        if not to_upload:
            logger.info(
                "No new documents to upload to vector store %s.", self.vector_store_id
            )
            return

        self._upload_documents(to_upload)

    def ingest_document(self, file_path: Path, *, allow_duplicates: bool = False) -> bool:
        """Upload a single document to the configured vector store.

        Returns True if the document was queued for upload, False if it already existed
        and duplicates are not allowed.
        """

        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Document path {file_path} does not exist")

        if not allow_duplicates:
            existing = self._existing_filenames()
            if file_path.name in existing:
                logger.info(
                    "Document %s already present in vector store %s; skipping upload.",
                    file_path.name,
                    self.vector_store_id,
                )
                return False

        self._upload_documents([file_path])
        return True

    def _upload_documents(self, files: Sequence[Path]) -> None:
        if not files:
            return

        logger.info(
            "Uploading %d document(s) to OpenAI vector store %s.",
            len(files),
            self.vector_store_id,
        )
        for file_path in files:
            try:
                with file_path.open("rb") as fh:
                    self.client.vector_stores.file_batches.upload_and_poll(
                        vector_store_id=self.vector_store_id,
                        files=[fh],
                    )
                logger.info("Uploaded %s to vector store.", file_path.name)
            except Exception as exc:  # pragma: no cover - best effort upload guard
                logger.exception("Failed to upload %s: %s", file_path, exc)

    def _existing_filenames(self) -> Dict[str, str]:
        filenames: Dict[str, str] = {}
        after: Optional[str] = None
        while True:
            response = self.client.vector_stores.files.list(
                vector_store_id=self.vector_store_id,
                limit=100,
                after=after,
            )
            for ref in response.data:
                file_id = getattr(ref, "file_id", None) or getattr(ref, "id", None)
                if not file_id:
                    continue
                try:
                    name = self._file_cache.filename(file_id)
                    filenames[name] = file_id
                except Exception:  # pragma: no cover - defensive
                    filenames[file_id] = file_id
            if not getattr(response, "has_more", False):
                break
            after = getattr(response, "last_id", None)
            if not after:
                break
        return filenames

    def _ensure_vector_store(self, name: str) -> str:
        """Return an existing vector store id or create a new store with the given name."""
        existing = self._find_vector_store_by_name(name)
        if existing:
            logger.info("Using existing OpenAI vector store %s (%s).", name, existing)
            return existing
        response = self.client.vector_stores.create(name=name)
        vector_store_id = getattr(response, "id", None)
        if not vector_store_id:
            raise RuntimeError("Failed to create OpenAI vector store")
        logger.info("Created OpenAI vector store %s (%s).", name, vector_store_id)
        return vector_store_id

    def _find_vector_store_by_name(self, name: str) -> Optional[str]:
        after: Optional[str] = None
        while True:
            response = self.client.vector_stores.list(limit=100, after=after)
            for store in response.data:
                store_name = getattr(store, "name", None)
                if store_name == name:
                    return getattr(store, "id", None)
            if not getattr(response, "has_more", False):
                break
            after = getattr(response, "last_id", None)
            if not after:
                break
        return None

    # ---------------------------------------------------------------------#
    # Retrieval operations                                                 #
    # ---------------------------------------------------------------------#
    def ask(
        self,
        question: str,
        *,
        k: Optional[int] = None,
        answer_lang: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, List[Hit]]:
        """Answer a question using the configured vector store."""
        top_k = k or self.default_top_k
        system_prompt = (
            "You are a document-grounded knowledge assistant. Use the provided documents "
            "to craft concise, helpful answers. Always cite sources inline using "
            "square brackets with the document name and page number when available."
        )
        if answer_lang:
            system_prompt += f" Respond in {answer_lang}."

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": question}],
                },
            ],
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [self.vector_store_id],
                    "max_num_results": top_k,
                }
            ],
            max_output_tokens=800,
            metadata=metadata,
        )

        answer = self._extract_text(response)
        hits = self._extract_hits(response)
        return answer, hits[:top_k]

    def search(self, query: str, *, k: Optional[int] = None) -> List[Hit]:
        """Return the top-k supporting snippets without generating an answer."""
        _, hits = self.ask(query, k=k)
        return hits[: k or self.default_top_k]

    # ---------------------------------------------------------------------#
    # Internal helpers                                                     #
    # ---------------------------------------------------------------------#
    def _extract_text(
        self, response: Any
    ) -> str:
        text_parts: List[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) != "output_text":
                    continue
                text_obj = getattr(content, "text", None)
                if isinstance(text_obj, str):
                    text_parts.append(text_obj)
                elif text_obj is not None:
                    value = getattr(text_obj, "value", None)
                    if value:
                        text_parts.append(value)
        if text_parts:
            return "".join(text_parts).strip()
        # Fallback for helper property available in newer SDKs.
        fallback = getattr(response, "output_text", None)
        if isinstance(fallback, str):
            return fallback or ""
        return ""

    def _extract_hits(
        self, response: Any
    ) -> List[Hit]:
        hits: List[Hit] = []
        seen: Dict[str, Hit] = {}

        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) != "output_text":
                    continue
                annotations: List[Any] = []
                text_obj = getattr(content, "text", None)
                if text_obj is not None and hasattr(text_obj, "annotations"):
                    annotations.extend(getattr(text_obj, "annotations") or [])
                content_annotations = getattr(content, "annotations", None)
                if content_annotations:
                    annotations.extend(content_annotations)
                for annotation in annotations:
                    if getattr(annotation, "type", None) != "file_citation":
                        continue
                    file_citation = getattr(annotation, "file_citation", None)
                    file_id = getattr(annotation, "file_id", None)
                    page = getattr(annotation, "page", None)
                    quote = getattr(annotation, "quote", None)
                    score = getattr(annotation, "score", 0.0)
                    if file_citation:
                        file_id = getattr(file_citation, "file_id", file_id)
                        page = getattr(file_citation, "page", page)
                        quote = getattr(file_citation, "quote", quote)
                        score = getattr(file_citation, "score", score)
                    if not file_id:
                        continue
                    key = f"{file_id}:{page}:{quote}"
                    if key in seen:
                        continue
                    filename = getattr(annotation, "filename", None)
                    if not filename:
                        try:
                            filename = self._file_cache.filename(file_id)
                        except Exception:  # pragma: no cover - defensive fallback
                            filename = file_id
                    snippet = quote or ""
                    if not snippet and isinstance(text_obj, str):
                        start = getattr(annotation, "start_index", None)
                        length = getattr(annotation, "length", None)
                        if start is not None and length:
                            snippet = text_obj[start : start + length]
                    hit = Hit(
                        score=float(score or 0.0),
                        text=snippet,
                        source=filename,
                        page=int(page or 0),
                        file_id=file_id,
                    )
                    hits.append(hit)
                    seen[key] = hit
        return hits
