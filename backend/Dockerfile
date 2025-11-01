FROM ghcr.io/astral-sh/uv:python3.11-alpine
RUN apk add --no-cache build-base lz4-dev zlib-dev zstd-dev

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
