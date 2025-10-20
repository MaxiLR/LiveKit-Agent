"""Configuration helpers for the standalone RAG HTTP service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool_env(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default)
    return value.lower() in {"1", "true", "yes", "on"}


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        services_dir = parent / "services"
        if (parent / "storage").exists() and (
            services_dir / "livekit_agent"
        ).exists() and (services_dir / "rag_service").exists():
            return parent
    return current.parents[len(current.parents) - 1]


BASE_DIR = _find_project_root()
DEFAULT_ENV_PATHS = [
    BASE_DIR / "services" / "rag_service" / ".env",
    BASE_DIR / ".env",
]

for env_path in DEFAULT_ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path, override=False)


@dataclass(slots=True)
class Settings:
    """Runtime configuration derived from environment variables."""

    storage_dir: Path = Path(os.getenv("RAG_STORAGE_DIR", BASE_DIR / "storage"))
    documents_dir: Path = Path(
        os.getenv("RAG_DOCUMENTS_DIR", storage_dir / "documents")
    )
    index_dir: Path = Path(os.getenv("RAG_INDEX_DIR", storage_dir / "indexes"))
    embed_model: str = os.getenv("RAG_EMBED_MODEL", "intfloat/multilingual-e5-base")
    service_host: str = os.getenv("RAG_SERVICE_HOST", "127.0.0.1")
    service_port: int = int(os.getenv("RAG_SERVICE_PORT", "8081"))
    default_top_k: int = int(os.getenv("RAG_SERVICE_TOP_K", "6"))
    enable_rerank: bool = _bool_env("RAG_ENABLE_RERANK", "true")
    rerank_model: str = os.getenv(
        "RAG_RERANK_MODEL", "BAAI/bge-reranker-v2-m3"
    )


settings = Settings()
