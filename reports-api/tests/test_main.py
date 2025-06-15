from fastapi.testclient import TestClient
from fastapi import status
import pytest
from typing import Dict, Callable
from datetime import datetime, timedelta
import time
import os
import base64
import json
import httpx
import httpcore

import logging

logging.basicConfig(level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.DEBUG))
logger = logging.getLogger(__name__)

JWT_VALID = os.getenv("JWT_VALID")
JWT_VALID_WRONG_USER = os.getenv("JWT_VALID_WRONG_USER")
JWT_EXPIRED = os.getenv("JWT_EXPIRED")
KEYCLOAK_ALLOWED_ROLE = os.getenv("KEYCLOAK_ALLOWED_ROLE")

REPORTS_API_URL = os.getenv("REPORTS_API_URL")
if not REPORTS_API_URL: raise ValueError("REPORTS_API_URL environment variable is not set or empty.")

def setup_module():
    """poor-man workaround for Podman inability to properly wait for a dependent service.
    See https://github.com/containers/podman-compose/issues/1183
    """
    for repeats in range(5):
        try:
            response = httpx.get(f"{REPORTS_API_URL}/ping")
        except httpcore.ConnectError as e:
            logger.info("unable to connect to API server: %s", e)
            time.sleep(5)
        else:
            break

def test_get_reports_no_token():
    response = httpx.get(f"{REPORTS_API_URL}/reports")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.skipif(not JWT_VALID, reason="JWT_VALID environment variable is not set or empty.")
def test_get_reports_success():
    try:
        claims = decode_jwt(JWT_VALID)
    except Exception as e:
        pytest.skip(f"Unable to decode JWT_VALID {e}")
    if is_expired(claims):
        pytest.skip("JWT_VALID is expired or not ready")
    response = httpx.get(f"{REPORTS_API_URL}/reports", headers={"Authorization": f"Bearer {JWT_VALID}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_id"] == claims["sub"]

@pytest.mark.skipif(not JWT_VALID_WRONG_USER,
    reason="JWT_VALID_WRONG_USER environment variable is not set or empty."
)
def test_get_reports_wrong_user():
    try:
        claims = decode_jwt(JWT_VALID_WRONG_USER)
    except Exception as e:
        pytest.skip(f"Unable to decode JWT_VALID_WRONG_USER: {e}")
    if is_expired(claims):
        pytest.skip("JWT_VALID_WRONG_USER is expired or not ready")

    response = httpx.get(f"{REPORTS_API_URL}/reports", headers={"Authorization": f"Bearer {JWT_VALID_WRONG_USER}"})
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.skipif(not JWT_EXPIRED, reason="JWT_EXPIRED environment variable is not set or empty.")
def test_get_reports_expired():
    try:
        claims = decode_jwt(JWT_EXPIRED)
    except Exception as e:
        pytest.skip(f"Unable to decode JWT_EXPIRED: {e}")
    if not is_expired(claims):
        pytest.skip("JWT_EXPIRED token is not expired")
    response = httpx.get(f"{REPORTS_API_URL}/reports", headers={"Authorization": f"Bearer {JWT_EXPIRED}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
@pytest.mark.skipif(not JWT_EXPIRED, reason="JWT_EXPIRED environment variable is not set or empty.")
def test_get_reports_modified():
    # try to extend expired token (should fail due to signature fail)
    def modify_claims(claims: Dict[str, str]) -> Dict[str, str]:
        current_ts = time.mktime(datetime.now().timetuple())
        if claims["iat"] > current_ts:
            claims["iat"] = int(current_ts) - 300
        if claims["exp"] <= current_ts:
            claims["exp"] = int(current_ts) + 300
        return claims

    try:
        new_token = modify_jwt(JWT_EXPIRED, modify_claims)
    except Exception as e:
        logger.exception("unable to modify JWT_EXPIRED")
        pytest.skip(f"Unable to modify JWT_EXPIRED {e}")
    logger.debug("modified JWT '%s'", new_token)
    response = httpx.get(f"{REPORTS_API_URL}/reports", headers={"Authorization": f"Bearer {new_token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def decode_jwt_payload(payload_encoded: str) -> Dict[str, str]:
    """
    Декодирует JWT payload и извлекает claims.
    """
    # Добавляем padding, если нужно (для корректного Base64 декодирования)
    payload_encoded += '=' * (4 - len(payload_encoded) % 4)
    
    # Декодируем из Base64URL -> UTF-8
    payload_decoded = base64.urlsafe_b64decode(payload_encoded).decode('utf-8')
    
    # Парсим JSON в словарь
    return json.loads(payload_decoded)

def encode_jwt_payload(claims: Dict[str, str]) -> str:
    """
    Кодирует claims в виде строки, пригодной для формирования JWT
    """
    bs = json.dumps(claims, indent=None, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return base64.urlsafe_b64encode(bs).strip(b'=').decode("utf-8")

def decode_jwt(token: str) -> Dict[str, str]:
    """
    Декодирует JWT и извлекает claims без проверки подписи.
    """
    # Разбиваем токен на части (header, payload, signature)
    _, payload_encoded, _ = token.split('.')
    return decode_jwt_payload(payload_encoded)        

def modify_jwt(token: str, modify_cb: Callable[[Dict[str, str]], Dict[str, str]]) -> str:
    """
    Модифицирует JWT claims при помощи предоставленного колбэка. Подпись не обновляется!
    """
    header, payload_encoded, sig = token.split('.')
    claims = decode_jwt_payload(payload_encoded)
    new_claims = modify_cb(claims)
    logger.debug("new claims: %s", new_claims)
    new_payload_encoded = encode_jwt_payload(new_claims)
    return '.'.join((header, new_payload_encoded, sig))

def is_expired(claims: Dict[str, str]) -> bool:
    current_ts = time.mktime(datetime.now().timetuple())
    logger.debug("current_ts=%d, exp=%d, iat=%d", current_ts, claims["exp"], claims["iat"])
    return current_ts >= claims["exp"] or current_ts <= claims["iat"]
