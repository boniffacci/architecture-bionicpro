from datetime import date
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Path, status
from pydantic import BaseModel
from clickhouse_driver import Client as ClickHouseClient
import jwt  # PyJWT


# ==== Конфигурация (в бою выносится в env) ====

CLICKHOUSE_HOST = "clickhouse"
CLICKHOUSE_DB = "bionicpro"

JWT_ISSUER = "http://localhost:8080/realms/reports-realm"
JWT_AUDIENCE = "reports-api"
JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
PASTE_KEYCLOAK_REALM_PUBLIC_KEY_HERE
-----END PUBLIC KEY-----"""


# ==== Модели ====

class ReportItem(BaseModel):
    report_date: date
    prosthesis_id: int
    total_active_sec: int
    avg_reaction_ms: float
    movements_count: int
    errors_count: int
    battery_avg_pct: float
    crm_country: str
    crm_segment: str
    crm_tariff: str


class ReportResponse(BaseModel):
    user_id: int
    from_date: date
    to_date: date
    items: List[ReportItem]


# ==== Инфраструктура ====

def get_clickhouse_client() -> ClickHouseClient:
    return ClickHouseClient(host=CLICKHOUSE_HOST, database=CLICKHOUSE_DB)


def get_current_user_id(authorization: str = Header(...)) -> int:
    """
    Достаём user_id из access-токена.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token",
        )

    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            JWT_PUBLIC_KEY,
            algorithms=["RS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No user id (sub) in token",
        )

    try:
        return int(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User id in token has wrong format",
        )


# ==== Бизнес-логика выборки отчёта ====

def load_report_from_olap(
    *, user_id: int, from_date: date, to_date: date
) -> ReportResponse:
    ch = get_clickhouse_client()

    # проверяем, до какого дня есть данные
    max_date_row = ch.execute(
        "SELECT max(report_date) FROM report_user_prosthesis_daily"
    )[0]
    max_date: Optional[date] = max_date_row[0]

    if max_date is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report data is not ready yet",
        )

    if to_date > max_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Reports are available only up to {max_date}. "
                f"Requested period {to_date} is not yet processed by ETL."
            ),
        )

    rows = ch.execute(
        """
        SELECT
            report_date,
            prosthesis_id,
            total_active_sec,
            avg_reaction_ms,
            movements_count,
            errors_count,
            battery_avg_pct,
            crm_country,
            crm_segment,
            crm_tariff
        FROM report_user_prosthesis_daily
        WHERE user_id = %(user_id)s
          AND report_date BETWEEN %(from)s AND %(to)s
        ORDER BY report_date, prosthesis_id
        """,
        {
            "user_id": user_id,
            "from": from_date,
            "to": to_date,
        },
    )

    items = [
        ReportItem(
            report_date=row[0],
            prosthesis_id=row[1],
            total_active_sec=row[2],
            avg_reaction_ms=row[3],
            movements_count=row[4],
            errors_count=row[5],
            battery_avg_pct=row[6],
            crm_country=row[7],
            crm_segment=row[8],
            crm_tariff=row[9],
        )
        for row in rows
    ]

    return ReportResponse(
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        items=items,
    )


# ==== FastAPI ====

app = FastAPI(
    title="BionicPRO Reports API",
    description="Сервис выдачи отчётов по работе протезов из OLAP-витрины",
    version="1.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Вариант 1: отчёт по себе ----------

@app.get(
    "/reports/me",
    response_model=ReportResponse,
    summary="Получить отчёт по своему аккаунту",
)
def get_my_report(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Отчёт всегда строится по текущему пользователю.
    user_id берём из токена → пользователь не может
    подменить идентификатор в запросе.
    """
    if to_date is None:
        to_date = date.today()
    if from_date is None:
        from_date = to_date.fromordinal(max(to_date.toordinal() - 6, 1))

    return load_report_from_olap(
        user_id=current_user_id,
        from_date=from_date,
        to_date=to_date,
    )


# ---------- Вариант 2: отчёт по user_id с явной проверкой ----------

@app.get(
    "/reports/{user_id}",
    response_model=ReportResponse,
    summary="Получить отчёт по указанному пользователю (только про себя)",
)
def get_report_for_user(
    user_id: int = Path(..., description="ID пользователя, для которого нужен отчёт"),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Ограничение доступа: пользователь может получить отчёт
    только про самого себя. Если user_id в пути не совпадает
    с user_id из токена — возвращаем 403 Forbidden.
    """

    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can request report only for yourself",
        )

    if to_date is None:
        to_date = date.today()
    if from_date is None:
        from_date = to_date.fromordinal(max(to_date.toordinal() - 6, 1))

    return load_report_from_olap(
        user_id=current_user_id,
        from_date=from_date,
        to_date=to_date,
    )
