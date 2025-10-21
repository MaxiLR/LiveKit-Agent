# LiveKit-Agent Architecture

## Overview
- Purpose: provide a LiveKit-powered voice assistant that can join rooms, answer questions with RAG context pulled from knowledge-base documents, and surface transcripts in a web client.
- Core pieces: a LiveKit agent worker, a FastAPI token API, a standalone RAG HTTP service backed by OpenAI vector stores, and a Vite/React frontend.
- Languages & runtimes: Python 3.12 (uv-managed) for backend services, TypeScript + React 18 for the web client.
- Hosting model: services can run locally via uv or together via `docker-compose`; the RAG engine relies on OpenAI-hosted retrieval infrastructure rather than an in-repo database.

## Codebase Layout
- `services/livekit_agent/`: uv project containing two executables:
  - `agent.main:entrypoint` (script `livekit-backend`) launches the LiveKit agent worker.
  - `agent.token_api:app` (script `livekit-backend-api`) exposes `/api/livekit/token` for minting LiveKit access tokens.
  - `tools/` packages all `@function_tool` definitions, and `personality.md` stores the agent's instruction set loaded at runtime.
- `services/rag_service/`: uv project exposing a FastAPI service (`rag-service`) that wraps `packages/rag_core` OpenAI retrieval helpers.
- `packages/rag_core/`: shared Python package feeding OpenAI Responses + vector-store APIs, reused by both services.
- `frontend/`: Vite + React + Tailwind application (shadcn/ui component primitives) that requests tokens, joins LiveKit rooms, and renders real-time transcripts.
- `storage/documents/`: local document cache that the RAG service syncs into the OpenAI vector store (one sample CV PDF is checked in).

## Runtime Components & Data Flow
- **Frontend client** (`frontend/src/App.tsx`):
  - Collects a display name and room name via `JoinForm`.
  - Calls the backend token endpoint (`POST {VITE_BACKEND_URL}/api/livekit/token`) to mint a LiveKit access token.
  - Uses `<LiveKitRoom>` from `@livekit/components-react` to join the room, render audio, and stream transcriptions (`TranscriptPanel`).
  - Presents the call UI inside a fixed-height monochrome shell (`h-[82vh]`) so the conference area has a predictable footprint; transcript and knowledge panels clamp their height and become scrollable when content overflows.
  - Formats transcript bubbles with agent turns left-aligned and participant turns right-aligned using a pure black-and-white palette (Tailwind tokens and shadcn components were stripped of colour accents).
  - Fetches knowledge documents from the RAG service (`GET {VITE_RAG_SERVICE_URL}/documents`), displays the active vector store id, and uploads PDFs via `POST {VITE_RAG_SERVICE_URL}/documents` with inline status/error handling.
  - Keeps session controls (`SessionControls`) for audio start, mute/unmute, and leaving the call with simplified monochrome buttons.
- **Token API service** (`agent/token_api.py`):
  - FastAPI app with CORS configured from `BACKEND_API_ALLOWED_ORIGINS`.
  - Validates presence of `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` and issues JWTs via `livekit.api.AccessToken`.
  - Default TTL taken from `LIVEKIT_TOKEN_TTL_SECONDS` (default 3600 seconds).
- **LiveKit agent worker** (`agent/main.py`):
  - Loads env vars from `services/livekit_agent/.env` or repo `.env`.
  - Establishes `AgentSession` with Deepgram STT (`DG_STT_MODEL`), OpenAI LLM (`LLM_CHOICE`, default `gpt-4.1-mini`), OpenAI TTS, and Silero VAD.
  - Loads persona instructions from `personality.md` and registers tools provided by `tools/registry.py`.
  - Uses `RAGClient` to hit the external RAG service; falls back with user-friendly errors if the service is unavailable.
  - Sends proactive status updates during long-running retrieval (implemented in `tools/registry.py`) and greets users when sessions start.
  - Maintains the agent session across short disconnects so users can rejoin the same room without restarting; rejoin greetings and idle shutdown are governed by `LIVEKIT_AGENT_REJOIN_GRACE_SECONDS` (default 120 s) and `LIVEKIT_AGENT_REJOIN_GREETING_COOLDOWN` (default 5 s).
  - Rejoin welcome messages are issued through a guarded background task to avoid queuing multiple greetings and to comply with the `AgentSession.generate_reply` API returning a `SpeechHandle` instead of a coroutine.
- **RAG HTTP service** (`rag_service/main.py`):
  - On startup, instantiates `OpenAIRetriever`, which looks up or creates an OpenAI vector store named via `OPENAI_VECTOR_STORE_NAME` (default `livekit-agent-rag`).
  - Immediately synchronises every non-hidden, non-empty file under `storage/documents/` into that vector store when `OPENAI_SYNC_DOCUMENTS=true` (default) to guarantee fresh corpus coverage.
  - Exposes `/query` for answer generation with optional reranking and language forcing, `/search` for snippet-only retrieval, and `/documents` (GET/POST) for listing and uploading PDFs directly into the vector store.
  - Applies configurable CORS (`RAG_SERVICE_ALLOWED_ORIGINS`, default `*`) so the frontend can call the document endpoints from another origin, and rejects oversized uploads (`RAG_MAX_DOCUMENT_BYTES`, default 25 MB).
  - Requires `python-multipart` for handling the multipart uploads; the dependency is declared in `services/rag_service/pyproject.toml` and bundled in container builds.
  - Uses `RAGEngine` to normalize retriever hits into `SourcePayload` objects with filename, page, and score metadata.
- **Shared retrieval layer** (`rag_core/openai_retriever.py`):
  - Wraps OpenAI Responses API to issue file-backed queries.
  - Caches file metadata to minimise API calls and automatically uploads any documents missing from the vector store.
  - Provides `ingest_document()` so individual uploads from the RAG service skip redundant re-scans, and formats answers with inline citation directives so downstream agents can mention sources.

## External Integrations
- **LiveKit Cloud**: Required for real-time rooms, token minting, and LiveKit agent SDKs (`livekit`, `livekit-agents`, `livekit-client`).
- **OpenAI**:
  - Responses API (LLM generation and retrieval augmentation) within `OpenAIRetriever`.
  - Vector store for document embeddings that the service can auto-create and populate via the Python SDK.
  - Text-to-speech via `openai.TTS` in the LiveKit agent session.
- **Deepgram**: Speech-to-text streaming (`deepgram.STT`) for transcription within the agent worker.
- **Silero**: Voice activity detection (`silero.VAD`) for conversational responsiveness.
- **Docker Compose**: Optional orchestration bundling RAG service, token API, agent worker, and frontend behind shared network defaults.

## Data & Storage
- No relational database is provisioned; persistent knowledge comes from the OpenAI vector store.
- Local documents reside under `storage/documents/`; used for automatic syncing into the vector store and as a tracked reference to the source material.
- Runtime metadata (tokens, transcripts) stays in memory—there is no persistence layer for session transcripts.

## Configuration & Environment
- **LiveKit agent**:
  - `services/livekit_agent/.env.example` documents required LiveKit/OpenAI/Deepgram keys and `RAG_SERVICE_URL`.
  - Optional overrides: `LLM_CHOICE`, `DG_STT_MODEL`, `BACKEND_API_*`, `RAG_RERANK_ENABLED`, `LIVEKIT_AGENT_REJOIN_GRACE_SECONDS`, `LIVEKIT_AGENT_REJOIN_GREETING_COOLDOWN`.
- **RAG service**:
  - `.env.example` highlights optional `OPENAI_VECTOR_STORE_ID`, the store name override `OPENAI_VECTOR_STORE_NAME`, the model (`OPENAI_RAG_MODEL`), and the auto-sync toggle (`OPENAI_SYNC_DOCUMENTS`, default `true`).
  - `RAG_SERVICE_HOST`, `RAG_SERVICE_PORT`, `RAG_SERVICE_TOP_K` control exposed network behaviour.
  - `RAG_SERVICE_ALLOWED_ORIGINS` (comma-separated, default `*`) drives CORS for the HTTP API; `RAG_MAX_DOCUMENT_BYTES` caps upload size (bytes, default 26,214,400 ≈ 25 MB).
- **Frontend**:
  - `.env.example` defines `VITE_LIVEKIT_WS_URL` (WebSocket endpoint), `VITE_BACKEND_URL`, and `VITE_RAG_SERVICE_URL` (base URL for the RAG document API).
  - The sidebar reflects the live vector store contents; the legacy `VITE_AGENT_DOCUMENTS` seed list is no longer read.
- **Docker**:
  - `docker-compose.yml` wires containers with shared `.env` files, mounts `./storage`, and publishes ports `8081`, `8000`, `5173`.

## Operational Notes
- Start order matters: the RAG service must be reachable before the agent worker starts; the token API depends on LiveKit credentials, and the frontend needs both LiveKit WebSocket and backend URLs configured.
- Long-running retrieval requests trigger status messages to users; add monitoring on the RAG service’s `/health` endpoint for readiness.
- Auto-creation of the vector store happens on every cold start; ensure the account has capacity for new stores or set `OPENAI_VECTOR_STORE_ID` to reuse an existing one.
- When `OPENAI_SYNC_DOCUMENTS=true`, ensure the OpenAI account’s rate limits can handle the file uploads triggered on startup.
- The agent greets participants again when they rejoin a room after leaving, so repeated sessions in the same room remain conversational without requiring manual prompts.

## Related Docs
- `.agent/README.md` — documentation index and navigation guidance (create/update alongside this file).
