"""Lightweight FastAPI service that mints LiveKit access tokens for the frontend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from pydantic import BaseModel, Field, field_validator
import uvicorn


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
    BASE_DIR / ".env",  # optional shared overrides
]

for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path, override=False)


class TokenRequest(BaseModel):
    identity: str = Field(..., min_length=1, max_length=128)
    room: str = Field(..., min_length=1, max_length=128)

    @field_validator("identity", "room", mode="before")
    @classmethod
    def strip_value(cls, value: str) -> str:
        return value.strip()


class TokenResponse(BaseModel):
    token: str


@dataclass(slots=True)
class TokenConfig:
    api_key: str
    api_secret: str
    ttl_seconds: int = int(os.getenv("LIVEKIT_TOKEN_TTL_SECONDS", "3600"))


def get_config() -> TokenConfig:
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LiveKit credentials are not configured on the server.",
        )
    return TokenConfig(api_key=api_key, api_secret=api_secret)


app = FastAPI(title="LiveKit Backend API", version="0.1.0")

allowed_origins = {
    origin.strip()
    for origin in os.getenv(
        "BACKEND_API_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins) or ["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.post("/api/livekit/token", response_model=TokenResponse)
def create_access_token(
    payload: TokenRequest, config: Annotated[TokenConfig, Depends(get_config)]
) -> TokenResponse:
    try:
        video_grant = api.VideoGrants(room=payload.room, room_join=True)
        token = (
            api.AccessToken(config.api_key, config.api_secret)
            .with_identity(payload.identity)
            .with_ttl(timedelta(seconds=config.ttl_seconds))
            .with_grants(video_grant)
        )

        return TokenResponse(token=token.to_jwt())
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {exc}",
        ) from exc


def run() -> None:
    """Run the FastAPI app with uvicorn."""
    port = int(os.getenv("BACKEND_API_PORT", "8000"))
    host = os.getenv("BACKEND_API_HOST", "127.0.0.1")
    uvicorn.run("backend_app.token_api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
