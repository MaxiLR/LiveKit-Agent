"""Function tools exposed to the LiveKit agent runtime."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime
from typing import Iterable, TYPE_CHECKING

from langdetect import detect
from livekit.agents import RunContext
from livekit.agents.llm import FunctionTool, function_tool

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from agent.rag_client import RAGClient

logger = logging.getLogger(__name__)


def build_agent_tools(*, rag_client: "RAGClient", rag_top_k: int) -> Iterable[FunctionTool]:
    """Construct the function tools available to the voice agent."""

    async def _maybe_send_status_update(
        context: RunContext, query: str, delay_seconds: float = 0.75
    ) -> None:
        try:
            await asyncio.sleep(delay_seconds)
            await context.session.generate_reply(
                instructions=(
                    "Let the user know you're checking the knowledge base for "
                    f'"{query}" and it may take a few more seconds. Keep it brief.'
                ),
                allow_interruptions=False,
            )
        except asyncio.CancelledError:
            return
        except Exception:
            # Ignore status update failures so the primary tool work continues.
            return

    def _detect_lang(text: str) -> str | None:
        try:
            return detect(text)
        except Exception:
            return None

    @function_tool
    async def get_current_date_and_time(context: RunContext) -> str:
        """Return the current date and time formatted for natural dialogue."""
        current_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"The current date and time is {current_datetime}"

    @function_tool
    async def search_document_corpus(
        context: RunContext, query: str, citations: bool = True
    ) -> str:
        """Search the indexed document corpus and respond with grounded answers, including citations when available."""
        status_task = asyncio.create_task(
            _maybe_send_status_update(context, query=query)
        )
        try:
            rag_response = await asyncio.to_thread(
                rag_client.ask,
                query,
                k=rag_top_k,
                rerank=True,
                final_m=rag_top_k,
                answer_lang=_detect_lang(query),
            )
        except RuntimeError as exc:
            status_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await status_task
            logger.warning(
                "RAG request failed", extra={"query": query, "error": str(exc)}
            )
            return (
                "The retrieval service is currently unavailable. Please try again later."
                f"\n\nDetails: {exc}"
            )
        except Exception:
            status_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await status_task
            logger.exception("Unexpected failure during RAG retrieval", extra={"query": query})
            raise

        status_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await status_task

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

    return [get_current_date_and_time, search_document_corpus]
