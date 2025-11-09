from typing import Annotated

from fastapi import APIRouter, Cookie
from fastapi.responses import RedirectResponse

from bionicpro_auth.services.keycloak import KeycloakOpenIdService

router = APIRouter(prefix="/auth")

REDIRECT_URI = "http://localhost:8000/api/auth/callback"


@router.get("/url")
async def get_auth_url():
    koi_service = KeycloakOpenIdService()

    auth_url = await koi_service.get_auth_url(REDIRECT_URI)

    return RedirectResponse(auth_url)


@router.get("/callback")
async def process_callback(code: str, state: str):
    koi_service = KeycloakOpenIdService()

    session_key = await koi_service.exchange_code_for_session(code, state, REDIRECT_URI)

    response = RedirectResponse("http://localhost:3000")
    response.set_cookie(
        key="session_key",
        value=session_key,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return response


@router.get("/refresh")
async def refresh_token(
    session_key: Annotated[str | None, Cookie()] = None,
):
    koi_service = KeycloakOpenIdService()
    if not session_key:
        raise ValueError

    new_session_key = await koi_service.refresh_tokens(session_key)
    response = RedirectResponse("http://localhost:3000")
    response.set_cookie(
        key="session_key",
        value=new_session_key,
        httponly=True,
        secure=True,
    )

    return response
