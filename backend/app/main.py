import os
import time
from datetime import datetime
from functools import lru_cache
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
import jwt
import clickhouse_connect


KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", os.getenv("KEYCLOAK_URL", "http://keycloak:8080"))
KEYCLOAK_PUBLIC_URL = os.getenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")
API_AUDIENCE = os.getenv("API_AUDIENCE")  # optional: e.g. reports-api


app = FastAPI(title="BionicPRO Reports API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_origin_regex=r"https?://localhost:\\d+",
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"]
)


def _jwks_url() -> str:
    return f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"


def _issuer() -> str:
    return f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}"


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    with httpx.Client(timeout=10.0) as client:
        r = client.get(_jwks_url())
        r.raise_for_status()
        return r.json()


def get_public_key(token: str) -> Optional[str]:
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    keys = get_jwks().get("keys", [])
    for key in keys:
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    return None


def verify_token_and_get_subject(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]

    public_key = get_public_key(token)
    if public_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to resolve token key")

    options = {"verify_aud": API_AUDIENCE is not None}
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=API_AUDIENCE if API_AUDIENCE else None,
            options=options,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")

    # Явно валидируем issuer для публичного и внутреннего адресов
    token_iss = str(payload.get("iss", "")).rstrip("/")
    expected_suffix = f"/realms/{KEYCLOAK_REALM}"
    if not token_iss.endswith(expected_suffix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: Invalid issuer")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has no subject")
    return subject


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "ts": int(time.time())}
# Удаляем явный обработчик OPTIONS — CORS middleware ответит сам



def get_ch_client():
    host = os.getenv("CLICKHOUSE_HOST", "localhost")
    port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    user = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD", "")
    database = os.getenv("CLICKHOUSE_DB", "reports")
    return clickhouse_connect.get_client(host=host, port=port, username=user, password=password, database=database)


@app.get("/reports")
def get_report(current_user_sub: str = Depends(verify_token_and_get_subject), start: Optional[str] = None, end: Optional[str] = None) -> Response:
    client = get_ch_client()
    client.command("CREATE TABLE IF NOT EXISTS user_reports (user_sub String, ts DateTime, metric Float64) ENGINE = MergeTree ORDER BY (user_sub, ts)")
    client.command("CREATE TABLE IF NOT EXISTS load_markers (loaded_from DateTime, loaded_to DateTime) ENGINE = ReplacingMergeTree ORDER BY loaded_to")
    # Простая агрегированная выборка по пользователю с опциональным фильтром периода
    where_period = ""
    params = {"user_sub": current_user_sub}
    if start and end:
        # читаем последнюю доступную загрузку
        rows_marker = client.query("SELECT loaded_from, loaded_to FROM load_markers ORDER BY loaded_to DESC LIMIT 1").result_rows
        if not rows_marker:
            return Response(status_code=400, content=b"Requested period is not available: no markers")
        marker_from, marker_to = rows_marker[0]
        # парсим пришедшие границы
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
        except Exception:
            return Response(status_code=400, content=b"Invalid datetime format. Use ISO 8601, e.g. 2025-10-15T00:00:00")
        # валидация окна
        if start_dt < marker_from or end_dt > marker_to or start_dt > end_dt:
            msg = f"Requested period is not processed. Allowed: {marker_from.isoformat()}..{marker_to.isoformat()}".encode("utf-8")
            return Response(status_code=400, content=msg)
        where_period = " AND ts BETWEEN parseDateTimeBestEffort(%(start)s) AND parseDateTimeBestEffort(%(end)s)"
        params.update({"start": start, "end": end})
    query = f"SELECT user_sub, count() AS events, avg(metric) AS avg_metric FROM user_reports WHERE user_sub = %(user_sub)s{where_period} GROUP BY user_sub"
    rows = client.query(query, parameters=params).result_rows

    if rows:
        _, events, avg_metric = rows[0]
    else:
        events, avg_metric = 0, 0.0

    content = (
        f"Report for user {current_user_sub}\n"
        f"Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Events: {events}\n"
        f"Avg metric: {avg_metric}\n"
    ).encode("utf-8")

    headers = {"Content-Disposition": "attachment; filename=report.txt"}
    return Response(content=content, media_type="text/plain; charset=utf-8", headers=headers)


