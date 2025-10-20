# LiveKit-Agent

## Project Layout (scaffold)
- `services/livekit_agent/`: uv-managed Python project for the LiveKit agent entrypoint (`uv run livekit-backend`).
- `packages/rag_core/`: shared library with FAISS/PDF utilities consumed by both backend and services.
- `services/rag_service/`: FastAPI-based HTTP service exposing RAG APIs for multi-agent scenarios.
- `frontend/`: Vite + React client for joining the LiveKit room, managing the call lifecycle, and rendering live transcripts.
- `storage/`: persistent assets shared by services (`documents/` source PDFs, `indexes/` FAISS artifacts).

See `services/livekit_agent/.env.example` and `services/rag_service/.env.example` for configuration hints.

## Environment Configuration

- `services/livekit_agent/.env` — LiveKit, OpenAI, Deepgram credentials, and RAG client routing.
- `services/rag_service/.env` — storage locations, embedding model, and service port.
- `frontend/.env` — LiveKit WebSocket URL and backend token endpoint for the web client.
- `.env.example` at the repo root points to each template; copy the examples beside the services you intend to run.

## Running Locally

1. **Start the FastAPI token service** (used by the frontend to mint LiveKit tokens):
   ```bash
   cd services/livekit_agent
   uv run livekit-backend-api
   ```
   This listens on `http://127.0.0.1:8000/api/livekit/token` by default. Override `BACKEND_API_HOST` / `BACKEND_API_PORT` (and `BACKEND_API_ALLOWED_ORIGINS` for CORS) in `services/livekit_agent/.env` if needed.

2. **Run the LiveKit agent worker** (joins the room and powers the voice agent experience):
   ```bash
   cd services/livekit_agent
   uv run livekit-backend dev
   ```

3. *(Optional)* **Start the RAG service** if you want to offload retrieval:
   ```bash
   cd services/rag_service
   uv run rag-service
   ```

4. **Launch the frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Frontend Quickstart

1. Copy `frontend/.env.example` to `frontend/.env` and set:
   - `VITE_LIVEKIT_WS_URL` — your LiveKit Cloud/WebSocket URL (`wss://...`).
   - `VITE_BACKEND_URL` — base URL for the backend API that issues LiveKit access tokens.
2. Install dependencies from the `frontend/` directory with `npm install` (or `pnpm install`).
3. Launch the dev server via `npm run dev` and open the provided URL (defaults to http://localhost:5173).
4. Use the “Start Call” button to join the agent room, then monitor the real-time transcript and end the call with the “End Call” control.
