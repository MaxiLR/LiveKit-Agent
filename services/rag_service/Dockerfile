FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel uv

COPY packages ./packages
COPY services/rag_service ./services/rag_service

WORKDIR /app/services/rag_service
RUN uv sync --frozen --no-dev --python $(which python)

ENV VIRTUAL_ENV=/app/services/rag_service/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /app

EXPOSE 8081

CMD ["rag-service"]
