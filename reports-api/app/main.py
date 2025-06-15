from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.middleware.cors import CORSMiddleware

from keycloak import KeycloakOpenID
from jwcrypto.common import JWException

import os
from datetime import datetime, UTC, timedelta
from uuid import UUID
from uuid_extensions import uuid7

from typing import List, Optional
from pydantic import BaseModel, Field
import logging

logging.basicConfig(level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.DEBUG))
logger = logging.getLogger(__name__)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
if not KEYCLOAK_URL: raise ValueError("KEYCLOAK_URL environment variable is not specified or empty")

KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
if not KEYCLOAK_REALM: raise ValueError("KEYCLOAK_REALM environment variable is not specified or empty")

KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
if not KEYCLOAK_CLIENT_ID: raise ValueError("KEYCLOAK_CLIENT_ID environment variable is not specified or empty")

KEYCLOAK_ALLOWED_ROLE = os.getenv("KEYCLOAK_ALLOWED_ROLE")
if not KEYCLOAK_ALLOWED_ROLE: raise ValueError("KEYCLOAK_ALLOWED_ROLE environment variable is not specified or empty")

ALLOWED_CORS_ORIGINS=os.getenv("ALLOWED_CORS_ORIGINS", "http://localhost:3000").split("|")

secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
if not secret:
    KEYCLOAK_CLIENT_SECRET_FILE = os.getenv("KEYCLOAK_CLIENT_SECRET_FILE", "/run/secrets/keycloak_client_secret")
    try:
        logger.debug("loading client secret from %s", KEYCLOAK_CLIENT_SECRET_FILE)
        with open(KEYCLOAK_CLIENT_SECRET_FILE, "r") as secret_file:
            secret = secret_file.read().strip()
    except Exception as e:
        e.add_note(f"Unable to read secret from '{KEYCLOAK_CLIENT_SECRET_FILE}'")
        raise

keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_URL,
    client_id=KEYCLOAK_CLIENT_ID,
    realm_name=KEYCLOAK_REALM,
    client_secret_key=secret,
)

# Схема аутентификации OAuth2
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_URL}realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_URL}realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.debug("decoding and validating token '%s'", token)
    try:
        # Декодирование и проверка токена
        token_info = keycloak_openid.decode_token(token, validate=True)
    except JWException as e:
        logger.debug("an error while decoding token %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # probably some exceptions should be handled silently without being reported to logs
        logger.exception("unexpected exception")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request",
        )
        
    # Проверка наличия роли KEYCLOAK_ALLOWED_ROLE в токене
    user_roles = token_info.get("realm_access", {}).get("roles", [])
    if KEYCLOAK_ALLOWED_ROLE not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required role: {KEYCLOAK_ALLOWED_ROLE}",
        )
    
    return token_info

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Можно указать конкретные методы: ["GET", "POST", etc.]
    allow_headers=["*"],  # Можно указать конкретные заголовки
    expose_headers=["*"],  # Заголовки, которые могут быть доступны клиенту
)

class ReportRow(BaseModel):
    id: UUID = Field(description = 'ID показания')
    received: datetime = Field(description = 'время получения показания')
    status: str = Field(description = 'статус датчика')
    sensor: str = Field(description = 'название датчика')
    value: str = Field(description = 'значение датчика')

class Report(BaseModel):
    user_id: UUID = Field(description = 'ID пользователя')
    generated: datetime = Field(description = 'время генерации отчёта')
    rows: List[ReportRow] = Field(description = 'список показаний')

# Эндпойнт для получения отчетов (доступен только для KEYCLOAK_ALLOWED_ROLE)
@app.get("/reports", response_model=Report)
async def get_reports(current_user: dict = Depends(get_current_user)) -> list[Report]:
    logger.debug("building report for user '%(preferred_username)s' (sub=%(sub)s)", current_user)
    rows = [
        ReportRow(id=uuid7(), received=datetime.now(UTC) - timedelta(seconds=10), status="OK", sensor="sensor1", value="1"),
        ReportRow(id=uuid7(), received=datetime.now(UTC) - timedelta(seconds=5), status="Fail", sensor="sensor2", value="")
    ]
    return Report(user_id=UUID(current_user["sub"]), generated=datetime.now(UTC), rows=rows)

@app.get("/ping", response_model=str)
async def ping():
    return "pong"