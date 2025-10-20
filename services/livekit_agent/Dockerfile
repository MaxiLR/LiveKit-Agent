FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ffmpeg git curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel uv

COPY packages ./packages
COPY services/livekit_agent ./services/livekit_agent

WORKDIR /app/services/livekit_agent
RUN uv sync --frozen --no-dev --python $(which python)

ENV VIRTUAL_ENV=/app/services/livekit_agent/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /app

EXPOSE 8000

CMD ["livekit-backend-api"]
