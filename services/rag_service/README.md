# RAG Service

FastAPI application exposing shared retrieval features for multiple LiveKit agents.

## Vector Store Management
- On startup the service uses the `OPENAI_API_KEY` to locate or create an OpenAI vector store named via `OPENAI_VECTOR_STORE_NAME` (defaults to `livekit-agent-rag`).
- If `OPENAI_VECTOR_STORE_ID` is set, the existing store is reused; otherwise the service creates one and remembers it by name.
- Every launch uploads any files found under `${RAG_DOCUMENTS_DIR}` (defaults to `storage/documents/`) that are not already present in the vector store, skipping hidden files and zero-byte placeholders.
- Set `OPENAI_SYNC_DOCUMENTS=false` to skip the automatic upload.

## Key Environment Variables
- `OPENAI_API_KEY` — required; enables vector store creation and queries.
- `RAG_DOCUMENTS_DIR` — path to the local corpus to sync into the vector store.
- `OPENAI_RAG_MODEL` — Responses API model used for answer generation (default `gpt-4.1-mini`).
- `RAG_SERVICE_TOP_K` — default retrieval depth exposed by the HTTP API.
