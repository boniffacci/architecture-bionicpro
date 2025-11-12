from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, jwk, JWTError
import requests
import os
import uuid
import hashlib
from typing import Dict
from random import randint
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

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

        logging.warning(payload)

        roles = payload.get("realm_access", {}).get("roles", [])
        if "prothetic_user" not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")

        return payload

    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    

@app.get("/reports")
def get_reports(user: Dict = Depends(get_current_user)):
    user_id = user.get("sub", "unknown")
    logging.warning(user_id)

    db_config = {
            'host': os.environ.get("AIRFLOW_DB_HOST", "postgres"),
            'database': os.environ.get("AIRFLOW_DB_NAME", "sample"),
            'user': os.environ.get("AIRFLOW_DB_USER", "airflow"),
            'password': os.environ.get("AIRFLOW_DB_PASSWORD", "airflow"),
            'port': '5432'
        }
    
    connection = psycopg2.connect(**db_config)
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT * FROM olap_table
        WHERE user_id = %s
        """
    params = [user_id]

    cursor.execute(query, params)
    reports = [dict(row) for row in cursor.fetchall()]

    cursor.close()
    connection.close()

    return {"reports": reports}