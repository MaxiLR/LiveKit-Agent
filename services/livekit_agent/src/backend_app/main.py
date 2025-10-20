"""LiveKit voice assistant entrypoint integrating a PDF-based RAG knowledge base."""

from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv
from langdetect import detect
from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, openai, silero

from backend_app.rag_client import RAGClient


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        services_dir = parent / "services" / "livekit_agent"
        if services_dir.exists() and (parent / "storage").exists():
            return parent
    return current.parents[len(current.parents) - 1]


BASE_DIR = _find_project_root()

ENV_PATHS = [
    BASE_DIR / "services" / "livekit_agent" / ".env",
    BASE_DIR / ".env",  # fallback for shared overrides
]

for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path, override=False)

STORAGE_DIR = Path(os.getenv("RAG_STORAGE_DIR", BASE_DIR / "storage"))
DOCUMENTS_DIR = Path(os.getenv("RAG_DOCUMENTS_DIR", STORAGE_DIR / "documents"))
INDEX_DIR = Path(os.getenv("RAG_INDEX_DIR", STORAGE_DIR / "indexes"))
DEFAULT_EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "intfloat/multilingual-e5-base")


class Assistant(Agent):
    """Voice assistant augmented with a PDF-based knowledge base."""

    def __init__(self, rag_client: RAGClient, rag_top_k: int = 6):
        super().__init__(
            instructions=(
                "You are a friendly enterprise assistant for SaveApp. "
                "Use the `search_pdf_knowledge_base` tool whenever a question might be "
                "answered by the indexed documents. Always cite document name and page "
                "when you rely on retrieved context. Keep responses concise and natural. "
                "Respond in the user's language (detect automatically)."
            )
        )
        self._rag_client = rag_client
        self._rag_top_k = rag_top_k

    @function_tool
    async def get_current_date_and_time(self, context: RunContext) -> str:
        """Get the current date and time."""
        current_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"The current date and time is {current_datetime}"

    @function_tool
    async def search_pdf_knowledge_base(
        self, context: RunContext, query: str, citations: bool = True
    ) -> str:
        """Retrieve an answer grounded in the indexed PDF knowledge base."""
        try:
            rag_response = self._rag_client.ask(
                query,
                k=self._rag_top_k,
                rerank=True,
                final_m=self._rag_top_k,
                answer_lang=self._detect_lang(query),
            )
        except RuntimeError as exc:
            return (
                "The retrieval service is currently unavailable. Please try again later."
                f"\n\nDetails: {exc}"
            )
        sources = rag_response.sources
        if not sources:
            return "No relevant passages were found in the indexed documents."
        if not citations:
            return rag_response.answer
        formatted_sources = "\n".join(
            f"- {src.source} p.{src.page} (score={src.score:.2f}, lang={src.lang})"
            for src in sources
        )
        return f"{rag_response.answer}\n\nSources:\n{formatted_sources}"

    def _detect_lang(self, text: str) -> str | None:
        """Detect language code from text; returns None if detection fails."""
        try:
            return detect(text)
        except Exception:
            return None


async def entrypoint(ctx: agents.JobContext):
    """Entry point for the agent."""
    try:
        rag_client = RAGClient(
            documents_dir=DOCUMENTS_DIR,
            index_dir=INDEX_DIR,
            embed_model=DEFAULT_EMBED_MODEL,
            top_k=6,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "No PDF documents were found for indexing. "
            "Add PDFs to storage/documents before starting the agent."
        ) from exc

    session = AgentSession(
        stt=deepgram.STT(model=os.getenv("DG_STT_MODEL", "nova-2"), language="multi"),
        llm=openai.LLM(model=os.getenv("LLM_CHOICE", "gpt-4.1-mini")),
        tts=openai.TTS(voice="echo"),
        vad=silero.VAD.load(),
    )

    await session.start(room=ctx.room, agent=Assistant(rag_client=rag_client))

    await session.generate_reply(
        instructions="Greet the user warmly and ask how you can help."
    )


def run_cli() -> None:
    """Convenience entrypoint used by uv script."""
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    run_cli()
