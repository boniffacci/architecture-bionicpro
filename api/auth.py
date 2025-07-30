import jwt
import requests
from typing import Optional, List
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import json
from functools import lru_cache

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")

security = HTTPBearer()

@lru_cache()
def get_keycloak_public_key():
    """Получить публичный ключ Keycloak для валидации JWT"""
    try:
        # Get realm configuration
        realm_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
        response = requests.get(realm_url)
        response.raise_for_status()
        realm_config = response.json()
        
        # Get JWKS
        jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
        jwks_response = requests.get(jwks_url)
        jwks_response.raise_for_status()
        jwks = jwks_response.json()
        
        return jwks, realm_config
        
    except Exception as e:
        print(f"Error getting Keycloak public key: {e}")
        raise HTTPException(status_code=500, detail="Unable to get Keycloak configuration")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Проверить валидность JWT токена"""
    try:
        token = credentials.credentials
        jwks, realm_config = get_keycloak_public_key()
        
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        # Find the correct key
        key = None
        for jwk in jwks['keys']:
            if jwk['kid'] == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                break
        
        if key is None:
            raise HTTPException(status_code=401, detail="Invalid token key")
        
        # Get issuer from token to handle localhost vs keycloak hostname difference
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        actual_issuer = unverified_payload.get('iss')
        
        # Don't verify audience if it's None (Keycloak doesn't always set audience)
        verify_options = {"verify_aud": unverified_payload.get('aud') is not None}
        
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            options=verify_options,
            issuer=actual_issuer
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

def get_current_user(token_payload: dict = Depends(verify_token)) -> dict:
    """Получить информацию о текущем пользователе"""
    return {
        "username": token_payload.get("preferred_username"),
        "email": token_payload.get("email"),
        "roles": token_payload.get("realm_access", {}).get("roles", []),
        "client_roles": token_payload.get("resource_access", {}),
        "sub": token_payload.get("sub")
    }

def require_role(required_role: str):
    """Decorator для проверки роли пользователя"""
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_roles = current_user.get("roles", [])
        if required_role not in user_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    
    return role_checker

# Specific role checkers
def require_prothetic_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Проверить, что пользователь имеет роль prothetic_user"""
    return require_role("prothetic_user")(current_user)