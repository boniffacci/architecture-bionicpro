from typing import Annotated

from fastapi import APIRouter, Cookie

from bionicpro_auth.services.keycloak import KeycloakOpenIdService
from bionicpro_auth.services.reports import ReportService

router = APIRouter(prefix="/reports")


@router.get("/my")
async def get_my_report(
    session_key: Annotated[str | None, Cookie()] = None,
):
    koi_service = KeycloakOpenIdService()
    if not session_key:
        raise ValueError

    username = await koi_service.get_username(session_key)
    with ReportService() as report_service:
        return report_service.load_report(username)
