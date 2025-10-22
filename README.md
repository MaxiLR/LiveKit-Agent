# LiveKit-Agent

![LiveKit Agent](https://img.shields.io/badge/LiveKit%20Agent-Voice%20AI-black?logo=livekit&logoColor=white)

Conversational voice assistant that joins a LiveKit room, answers questions using OpenAI-powered retrieval, and streams transcripts in real time through a React frontend.

---

## Tech Stack Highlights

| Voice + Realtime | Web Client | AI & Retrieval | Runtime & Ops |
| --- | --- | --- | --- |
| ![LiveKit](https://img.shields.io/badge/LiveKit-000000?logo=livekit&logoColor=white) | ![React](https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original-wordmark.svg) | ![OpenAI](https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white) | ![Python](https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original-wordmark.svg) |
| ![Deepgram](https://img.shields.io/badge/Deepgram-101020?logo=deepgram&logoColor=00ADEF) | ![TypeScript](https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.svg) | ![Vector Store](https://img.shields.io/badge/OpenAI%20Vector%20Store-2C2C2C?logo=openai&logoColor=white) | ![FastAPI](https://cdn.jsdelivr.net/gh/devicons/devicon/icons/fastapi/fastapi-original-wordmark.svg) |
| ![Silero](https://img.shields.io/badge/Silero%20VAD-0B1E3F) | ![Vite](https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vitejs/vitejs-original.svg) | ![RAG](https://img.shields.io/badge/Retrieval%20Augmented%20Generation-111111) | ![Docker](https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original-wordmark.svg) |

> ℹ️  Dependencies are managed with `uv` (Python) and `npm` (frontend). See `.agent/System/project_architecture.md` for a deep architectural walkthrough.

---

## Quick Start (Docker Compose)

The fastest way to spin up the full stack—LiveKit agent worker, token API, RAG service, and frontend—is with Docker Compose.

1. Copy environment templates:
   ```bash
   cp services/livekit_agent/.env.example services/livekit_agent/.env
   cp services/rag_service/.env.example services/rag_service/.env
   cp frontend/.env.example frontend/.env
   ```
   Populate LiveKit, OpenAI, and Deepgram credentials, plus `VITE_LIVEKIT_WS_URL`, `VITE_BACKEND_URL`, and `VITE_RAG_SERVICE_URL`.

2. Launch everything:
   ```bash
   docker compose up --build
   ```
   - FastAPI token API is exposed on port `8000`.
   - RAG service listens on `8081`.
   - Frontend is available at `http://localhost:5173`.

3. Visit the frontend, join a room, and converse with the agent. Compose handles dependent start order so the RAG service is ready before the agent connects.

To tear everything down: `docker compose down` (add `-v` to remove volumes if desired).

---

## Manual Development Workflow

Prefer running services individually? Start them in this order:

1. **RAG HTTP service**
   ```bash
   cd services/rag_service
   uv run rag-service
   ```
2. **FastAPI token API**
   ```bash
   cd services/livekit_agent
   uv run livekit-backend-api
   ```
   Configure host/port/CORS in `services/livekit_agent/.env`.
3. **LiveKit agent worker**
   ```bash
   cd services/livekit_agent
   uv run livekit-backend dev
   ```
4. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Project Layout

- `services/livekit_agent/` — uv-managed Python app providing the agent worker (`livekit-backend`) and token API (`livekit-backend-api`).
- `services/rag_service/` — FastAPI service offering `/query`, `/search`, and `/documents` endpoints backed by OpenAI vector stores.
- `packages/rag_core/` — Shared retrieval utilities consumed by the agent and RAG service.
- `frontend/` — Vite + React UI for joining rooms, rendering transcripts, and managing knowledge documents.
- `storage/documents/` — Source PDFs synced into the OpenAI vector store.
- `.agent/` — Living documentation (architecture, SOPs, and feature plans). Start with `.agent/README.md`.

---

## Environment Templates

- `services/livekit_agent/.env` — LiveKit keys, RAG endpoint, LLM/STT/TTS model toggles.
- `services/rag_service/.env` — OpenAI vector store configuration and HTTP server settings.
- `frontend/.env` — Frontend URLs for LiveKit WebSocket, backend API, and RAG service.
- Root `.env.example` links to each service template for convenience.

---

## Contributing & Docs

1. Review `.agent/README.md` for the documentation index.
2. After modifying behaviour, update the relevant doc in `.agent/System`, `.agent/SOP`, or `.agent/Tasks`.
3. Keep `docker-compose.yml` and environment templates aligned with the docs to prevent drift.

Happy hacking! 🎧🧠
