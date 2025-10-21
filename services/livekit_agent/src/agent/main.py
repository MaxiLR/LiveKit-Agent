"""LiveKit voice assistant entrypoint backed by an external RAG service."""

from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from pathlib import Path
import time

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession
from livekit.agents.voice.room_io import RoomInputOptions
from livekit.plugins import deepgram, openai, silero

from agent.rag_client import RAGClient
from tools import build_agent_tools


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


def _float_env(name: str, default: float) -> float:
    """Best-effort float parsing for optional environment overrides."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


PERSONALITY_PATH = Path(__file__).resolve().parent.parent / "personality.md"


@lru_cache(maxsize=1)
def _load_personality() -> str:
    """Load the agent instruction set from the repository personality file."""

    try:
        instructions = PERSONALITY_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:  # pragma: no cover - configuration guardrail
        raise RuntimeError(
            f"Agent personality file missing at {PERSONALITY_PATH}."
        ) from exc

    if not instructions:
        raise RuntimeError(
            f"Agent personality file at {PERSONALITY_PATH} is empty; provide guidance text."
        )

    return instructions


logger = logging.getLogger(__name__)


class Assistant(Agent):
    """Voice assistant that delegates retrieval to the RAG HTTP service."""

    def __init__(self, rag_client: RAGClient, rag_top_k: int = 6) -> None:
        instructions = _load_personality()
        tools = build_agent_tools(rag_client=rag_client, rag_top_k=rag_top_k)
        super().__init__(instructions=instructions, tools=list(tools))


async def entrypoint(ctx: agents.JobContext):
    """Entry point for the agent."""

    try:
        rag_client = RAGClient(top_k=6)
    except RuntimeError as exc:
        raise RuntimeError(
            "RAG service is not configured. Ensure RAG_SERVICE_URL points to the "
            "standalone RAG HTTP service before starting the agent."
        ) from exc

    session = AgentSession(
        stt=deepgram.STT(model=os.getenv("DG_STT_MODEL", "nova-2"), language="multi"),
        llm=openai.LLM(model=os.getenv("LLM_CHOICE", "gpt-4.1-mini")),
        tts=openai.TTS(voice="echo"),
        vad=silero.VAD.load(),
        preemptive_generation=True,
    )

    assistant = Assistant(rag_client=rag_client)

    initial_greeting_sent = False
    last_rejoin_greet = 0.0
    pending_rejoin_greeting = False
    disconnect_token = 0.0
    rejoin_timeout_task: asyncio.Task[None] | None = None
    rejoin_greeting_task: asyncio.Task[None] | None = None
    rejoin_grace_seconds = _float_env("LIVEKIT_AGENT_REJOIN_GRACE_SECONDS", 120.0)
    rejoin_greeting_cooldown = _float_env("LIVEKIT_AGENT_REJOIN_GREETING_COOLDOWN", 5.0)
    remote_identity: str | None = None

    def _cancel_rejoin_timeout() -> None:
        nonlocal rejoin_timeout_task
        if rejoin_timeout_task is not None:
            rejoin_timeout_task.cancel()
            rejoin_timeout_task = None

    async def _close_after_disconnect(expected_token: float) -> None:
        try:
            await asyncio.sleep(rejoin_grace_seconds)
        except asyncio.CancelledError:
            return
        if (
            pending_rejoin_greeting
            and rejoin_grace_seconds > 0
            and disconnect_token == expected_token
        ):
            logger.info(
                "closing agent session after %.0fs without a participant rejoin",
                rejoin_grace_seconds,
            )
            await session.aclose()

    def _issue_welcome_back() -> None:
        nonlocal pending_rejoin_greeting, last_rejoin_greet, rejoin_greeting_task
        if not initial_greeting_sent or not pending_rejoin_greeting:
            return
        now = time.monotonic()
        if now - last_rejoin_greet < rejoin_greeting_cooldown:
            return
        if rejoin_greeting_task is not None and not rejoin_greeting_task.done():
            return
        pending_rejoin_greeting = False
        last_rejoin_greet = now
        _cancel_rejoin_timeout()
        async def _speak_welcome_back() -> None:
            try:
                await session.generate_reply(
                    instructions="Welcome back! I'm ready to continue whenever you are."
                )
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Failed to deliver welcome-back greeting")

        task = asyncio.create_task(
            _speak_welcome_back(), name="livekit-agent.rejoin-greeting"
        )

        def _clear_task(_: asyncio.Future) -> None:
            nonlocal rejoin_greeting_task
            if rejoin_greeting_task is task:
                rejoin_greeting_task = None

        task.add_done_callback(_clear_task)
        rejoin_greeting_task = task

    def _handle_user_state(event) -> None:
        if getattr(event, "new_state", None) not in {"listening", "speaking"}:
            return
        _issue_welcome_back()

    def _on_participant_connected(participant) -> None:
        nonlocal remote_identity
        try:
            local_identity = ctx.room.local_participant.identity
        except Exception:
            local_identity = None
        if local_identity and participant.identity == local_identity:
            return
        remote_identity = participant.identity
        _issue_welcome_back()

    def _on_participant_disconnected(participant) -> None:
        nonlocal pending_rejoin_greeting, disconnect_token, rejoin_timeout_task
        try:
            local_identity = ctx.room.local_participant.identity
        except Exception:
            local_identity = None
        if local_identity and participant.identity == local_identity:
            return
        if remote_identity is not None and participant.identity != remote_identity:
            return
        pending_rejoin_greeting = True
        disconnect_token = time.monotonic()
        _cancel_rejoin_timeout()
        if rejoin_grace_seconds > 0:
            rejoin_timeout_task = asyncio.create_task(
                _close_after_disconnect(disconnect_token)
            )

    def _handle_session_close(event) -> None:
        nonlocal pending_rejoin_greeting, remote_identity, rejoin_greeting_task
        pending_rejoin_greeting = False
        remote_identity = None
        _cancel_rejoin_timeout()
        if rejoin_greeting_task is not None:
            rejoin_greeting_task.cancel()
            rejoin_greeting_task = None
        ctx.room.off("participant_connected", _on_participant_connected)
        ctx.room.off("participant_disconnected", _on_participant_disconnected)

    session.on("user_state_changed", _handle_user_state)
    session.on("close", _handle_session_close)
    ctx.room.on("participant_connected", _on_participant_connected)
    ctx.room.on("participant_disconnected", _on_participant_disconnected)

    room_input_options = RoomInputOptions(close_on_disconnect=False)

    await session.start(
        room=ctx.room,
        agent=assistant,
        room_input_options=room_input_options,
    )

    for participant in ctx.room.remote_participants.values():
        _on_participant_connected(participant)

    await session.generate_reply(
        instructions="Greet the user warmly and ask how you can help."
    )
    initial_greeting_sent = True


def run_cli() -> None:
    """Convenience entrypoint used by uv script."""

    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    run_cli()
