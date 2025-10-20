"""Reusable PDF RAG utilities built on FAISS for both CLI and agent tooling."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple, Dict, Any

import faiss
import numpy as np
from langdetect import detect, DetectorFactory
from pypdf import PdfReader
# Avoid tokenizers parallelism fork warnings when service spawns workers.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from sentence_transformers import SentenceTransformer
from tqdm import tqdm

try:
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover - optional dependency
    CrossEncoder = None

DetectorFactory.seed = 0


@dataclass
class DocChunk:
    text: str
    source: str
    page: int
    lang: str = "unknown"


@dataclass
class Hit:
    score: float
    text: str
    source: str
    page: int
    lang: str = "unknown"


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    """Split text into slightly overlapping character windows that respect sentences."""
    text = " ".join(text.split())
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        cut = end
        for sep in [". ", "; ", ": ", "\n", " "]:
            pos = text.rfind(sep, start + int(chunk_size * 0.8), end)
            if pos != -1:
                cut = pos + len(sep)
                break
        chunks.append(text[start:cut].strip())
        if cut >= n:
            break
        start = max(cut - overlap, 0)
    return [c for c in chunks if c]


def extract_pdf_chunks(
    pdf_path: Path, chunk_size: int = 900, overlap: int = 150
) -> List[DocChunk]:
    reader = PdfReader(str(pdf_path))
    chunks: List[DocChunk] = []
    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if not txt.strip():
            continue
        for ch in chunk_text(txt, chunk_size=chunk_size, overlap=overlap):
            try:
                lang = detect(ch)
            except Exception:
                lang = "unknown"
            chunks.append(
                DocChunk(text=ch, source=pdf_path.name, page=i + 1, lang=lang)
            )
    return chunks


class PDFIndexer:
    """Owns the heavy lifting of turning PDFs into a FAISS index."""

    def __init__(
        self,
        embed_model: str = "intfloat/multilingual-e5-base",
        chunk_size: int = 900,
        overlap: int = 150,
    ) -> None:
        self.embed_model = embed_model
        self.chunk_size = chunk_size
        self.overlap = overlap

    def build(
        self,
        pdf_files: Iterable[Path],
        out_dir: Path,
        show_progress: bool = False,
    ) -> Dict[str, Any]:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_paths = [Path(p) for p in pdf_files if Path(p).is_file()]
        if not pdf_paths:
            raise ValueError("No PDF files provided for indexing.")

        iterator: Iterable[Path] = pdf_paths
        if show_progress:
            iterator = tqdm(pdf_paths, desc="Extracting chunks")

        all_chunks: List[DocChunk] = []
        for pdf in iterator:
            all_chunks.extend(
                extract_pdf_chunks(
                    pdf, chunk_size=self.chunk_size, overlap=self.overlap
                )
            )

        if not all_chunks:
            raise RuntimeError(
                "No textual content extracted. Check PDF OCR or permissions."
            )

        model = SentenceTransformer(self.embed_model)
        texts = [chunk.text for chunk in all_chunks]
        embeddings = model.encode(
            texts,
            batch_size=64,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings.astype(np.float32))

        faiss.write_index(index, str(out_dir / "index.faiss"))
        with open(out_dir / "meta.jsonl", "w", encoding="utf-8") as mf:
            for chunk in all_chunks:
                mf.write(
                    json.dumps(
                        {
                            "text": chunk.text,
                            "source": chunk.source,
                            "page": chunk.page,
                            "lang": chunk.lang,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        with open(out_dir / "config.json", "w", encoding="utf-8") as cf:
            json.dump(
                {
                    "embedding_model": self.embed_model,
                    "chunk_size": self.chunk_size,
                    "overlap": self.overlap,
                },
                cf,
                ensure_ascii=False,
                indent=2,
            )

        manifest = self._build_manifest(pdf_paths)
        with open(out_dir / "manifest.json", "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2, ensure_ascii=False)

        return manifest

    def _build_manifest(self, pdf_paths: Iterable[Path]) -> Dict[str, Any]:
        entries = []
        for pdf in pdf_paths:
            stat = pdf.stat()
            entries.append(
                {
                    "path": str(pdf.resolve()),
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
        return {
            "created_at": time.time(),
            "embedding_model": self.embed_model,
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
            "pdfs": entries,
        }


def load_index(
    out_dir: Path,
) -> Tuple[faiss.Index, List[Dict[str, Any]], SentenceTransformer, Dict[str, Any]]:
    """Load a previously built FAISS index with metadata and embedding model."""
    out_dir = Path(out_dir)
    index = faiss.read_index(str(out_dir / "index.faiss"))
    metas: List[Dict[str, Any]] = []
    with open(out_dir / "meta.jsonl", "r", encoding="utf-8") as mf:
        for line in mf:
            metas.append(json.loads(line))
    with open(out_dir / "config.json", "r", encoding="utf-8") as cf:
        cfg = json.load(cf)
    model = SentenceTransformer(cfg["embedding_model"])
    return index, metas, model, cfg


class PDFKnowledgeBase:
    """High-level helper that keeps a FAISS index in sync with a documents folder."""

    def __init__(
        self,
        documents_dir: Path,
        index_dir: Path,
        embed_model: str = "intfloat/multilingual-e5-base",
        chunk_size: int = 900,
        overlap: int = 150,
    ) -> None:
        self.documents_dir = Path(documents_dir)
        self.index_dir = Path(index_dir)
        self.indexer = PDFIndexer(embed_model, chunk_size, overlap)
        self._model: SentenceTransformer | None = None
        self._index: faiss.Index | None = None
        self._metas: List[Dict[str, Any]] = []
        self._cfg: Dict[str, Any] = {}

    @classmethod
    def load_from_index(cls, index_dir: Path) -> "PDFKnowledgeBase":
        instance = cls(
            documents_dir=Path(index_dir),
            index_dir=Path(index_dir),
        )
        instance._load_index()
        return instance

    def ensure_index(self, show_progress: bool = False) -> None:
        pdf_files = sorted(self.documents_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(
                f"No PDFs found under {self.documents_dir}. Populate it before starting the agent."
            )
        if self._needs_rebuild(pdf_files):
            self.indexer.build(pdf_files, self.index_dir, show_progress=show_progress)
        self._load_index()

    def _needs_rebuild(self, pdf_files: List[Path]) -> bool:
        required_files = ["index.faiss", "meta.jsonl", "config.json", "manifest.json"]
        for name in required_files:
            if not (self.index_dir / name).exists():
                return True

        try:
            stored_manifest = json.loads(
                (self.index_dir / "manifest.json").read_text(encoding="utf-8")
            )
        except Exception:
            return True

        current_manifest = self.indexer._build_manifest(pdf_files)
        keys_to_check = ["embedding_model", "chunk_size", "overlap"]
        for key in keys_to_check:
            if stored_manifest.get(key) != current_manifest.get(key):
                return True

        stored_pdfs = {
            entry["path"]: entry for entry in stored_manifest.get("pdfs", [])
        }
        for pdf in pdf_files:
            resolved = str(pdf.resolve())
            stat = pdf.stat()
            entry = stored_pdfs.get(resolved)
            if entry is None:
                return True
            if (
                entry.get("size") != stat.st_size
                or entry.get("mtime_ns") != stat.st_mtime_ns
            ):
                return True

        if len(stored_pdfs) != len(pdf_files):
            return True

        return False

    def _load_index(self) -> None:
        if self._index is not None and self._model is not None:
            return
        self._index = faiss.read_index(str(self.index_dir / "index.faiss"))
        self._metas = []
        with open(self.index_dir / "meta.jsonl", "r", encoding="utf-8") as mf:
            for line in mf:
                self._metas.append(json.loads(line))
        with open(self.index_dir / "config.json", "r", encoding="utf-8") as cf:
            self._cfg = json.load(cf)
        self._model = SentenceTransformer(self._cfg["embedding_model"])

    def close(self) -> None:
        self._index = None
        self._model = None
        self._metas = []
        self._cfg = {}

    def search(self, query: str, k: int = 5) -> List[Hit]:
        if self._index is None or self._model is None:
            raise RuntimeError("Index not loaded. Call ensure_index() first.")
        query_emb = self._model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )
        D, I = self._index.search(query_emb.astype(np.float32), k)
        hits: List[Hit] = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(self._metas):
                continue
            meta = self._metas[idx]
            hits.append(
                Hit(
                    score=float(score),
                    text=meta["text"],
                    source=meta["source"],
                    page=int(meta["page"]),
                    lang=meta.get("lang", "unknown"),
                )
            )
        return hits

    def rerank(
        self, question: str, hits: List[Hit], model_name: str, top_m: int
    ) -> List[Hit]:
        if CrossEncoder is None:
            raise RuntimeError(
                "sentence-transformers CrossEncoder not available. Install torch dependencies."
            )
        cross_encoder = CrossEncoder(model_name)
        pairs = [(question, hit.text) for hit in hits]
        scores = cross_encoder.predict(pairs).tolist()
        rescored = sorted(zip(scores, hits), key=lambda item: item[0], reverse=True)
        top_hits = [
            Hit(
                score=float(score),
                text=hit.text,
                source=hit.source,
                page=hit.page,
                lang=hit.lang,
            )
            for score, hit in rescored[:top_m]
        ]
        return top_hits

    def build_prompt(self, question: str, hits: List[Hit], answer_lang: str | None):
        context_blocks = []
        for hit in hits:
            tag = f"{hit.source} p.{hit.page}"
            context_blocks.append(f"[{tag}]\n{hit.text}")
        context = "\n\n".join(context_blocks)
        target_lang = answer_lang
        if target_lang is None:
            try:
                target_lang = detect(question)
            except Exception:
                target_lang = "en"
        instructions = (
            "Use only the provided context to answer. "
            "If the answer is not present, state that it does not appear in the documents.\n"
            "Cite sources in the format (file p.X). "
            "Be concise and respond in the indicated language.\n"
            f"Answer language: {target_lang}.\n"
        )
        prompt = f"""{instructions}
Question: {question}

Context:
{context}

Answer:"""
        return prompt

    def call_ollama(
        self,
        prompt: str,
        model: str | None = None,
        host: str | None = None,
        timeout: int = 120,
    ) -> str:
        import requests

        model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct")
        host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        url = f"{host.rstrip('/')}/api/generate"
        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("response", "").strip()

    def call_openai(self, prompt: str, model: str | None = None) -> str:
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - import runtime guard
            raise RuntimeError(
                "openai>=1.0 is required to call the OpenAI API."
            ) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured.")
        model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a rigorous assistant. Respond in the indicated language "
                        "and cite sources at the end."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    def answer(
        self,
        question: str,
        k: int = 6,
        llm: str = "auto",
        use_rerank: bool = False,
        rerank_model: str = "BAAI/bge-reranker-v2-m3",
        final_m: int = 6,
        answer_lang: str | None = None,
    ) -> Tuple[str, List[Hit]]:
        hits = self.search(question, k=k)
        if use_rerank and hits:
            top_m = min(final_m, len(hits))
            hits = self.rerank(question, hits, model_name=rerank_model, top_m=top_m)

        prompt = self.build_prompt(question, hits, answer_lang=answer_lang)

        if llm == "ollama" or (llm == "auto" and os.getenv("OLLAMA_MODEL")):
            response = self.call_ollama(prompt)
        else:
            response = self.call_openai(prompt)
        return response, hits
