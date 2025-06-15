# syntax=docker/dockerfile:1.7-labs

FROM python:3-alpine AS builder

ENV PIP_CACHE_DIR=/var/cache/pip \
    PIPENV_VENV_IN_PROJECT=1

WORKDIR /app
RUN --mount=type=bind,source=./Pipfile,target=/app/Pipfile \
    --mount=type=bind,source=./Pipfile.lock,target=/app/Pipfile.lock \
    --mount=type=cache,target=/var/cache/pip \
<<EOF
set -e
pip install --root-user-action=ignore pipenv
pipenv install --deploy
# pipenv scan
EOF

FROM python:3-alpine

# define some required environment variables used throughout the application
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_PORT=8000 \
    APP_MODE=${APP_MODE:-PROD}

# declare environment variables
ENV LOG_LEVEL={$LOG_LEVEL} \
    KEYCLOAK_URL=${KEYCLOAK_URL} \
    KEYCLOAK_REALM=${KEYCLOAK_REALM} \
    KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID} \
    KEYCLOAK_CLIENT_SECRET_FILE=${KEYCLOAK_CLIENT_SECRET_FILE} \
    KEYCLOAK_ALLOWED_ROLE=${KEYCLOAK_ALLOWED_ROLE} \
    ALLOWED_CORS_ORIGINS=${ALLOWED_CORS_ORIGINS}

EXPOSE ${APP_PORT}

WORKDIR /app

RUN adduser -S -D -H appuser

COPY --from=builder /app /app

COPY --exclude=test_*.py ./app/ ./fastapi-wrapper.sh /app/

USER appuser

ENTRYPOINT [ "./fastapi-wrapper.sh", "main.py" ]