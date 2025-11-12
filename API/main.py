from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode
import requests
import os
import uuid
import hashlib
from typing import Dict
from random import randint

app = FastAPI()

origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["authorization"],
)

bearer_scheme = HTTPBearer()


KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "reports-realm")

KEYCLOAK_ISSUER = "http://localhost:8080/realms/reports-realm"
KEYCLOAK_CERTS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"


def get_certs():
    response = requests.get(KEYCLOAK_CERTS_URL)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch Keycloak public keys")
    return response.json()

def get_current_user(token: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        unverified_header = jwt.get_unverified_header(token.credentials)
        kid = unverified_header.get("kid")

        keys = get_certs()["keys"]
        key = next((k for k in keys if k["kid"] == kid), None)
        if not key:
            raise Exception("Public key not found")

        public_key = jwk.construct(key)

        payload = jwt.decode(
            token.credentials,
            public_key,
            algorithms=[key["alg"]],
            audience="reports-api",
            issuer=KEYCLOAK_ISSUER
        )

        roles = payload.get("realm_access", {}).get("roles", [])
        if "prothetic_user" not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")

        return payload

    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    #except Exception as e:
    #   print(f"[DEBUG] Token validation failed: {e}")
    #   raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.get("/reports")
def get_reports(user: Dict = Depends(get_current_user)):
    user_id = user.get("sub", "unknown")

    # Генерируем 1–5 устройств для пользователя на основе user_id
    hash_digest = hashlib.sha256(user_id.encode()).hexdigest()
    device_count = 1 + int(hash_digest[0], 16) % 5

    reports = []
    for i in range(device_count):
        seed = f"{user_id}-{i}"
        device_uuid = str(uuid.UUID(hashlib.sha256(seed.encode()).hexdigest()[:32]))
        report = {
            "device": device_uuid,
            "reportId": str(uuid.uuid4()),
            "value": randint(20, 95)
        }
        reports.append(report)

    return {"reports": reports}