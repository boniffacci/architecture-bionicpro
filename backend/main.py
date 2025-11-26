from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from clickhouse_driver import Client
from jose import jwt, JWTError
import requests
import os
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI()

# --- Config ---
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse_password")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")

# Настройка CORS (чтобы фронтенд с localhost:3000 мог делать запросы)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # В продакшене здесь должен быть конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Схема авторизации (для Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token")

# Модели данных
class ReportItem(BaseModel):
    report_date: str
    client_name: str
    avg_battery_level: float
    total_steps: int
    max_muscle_voltage: float
    errors_count: int

# --- Security ---
def get_current_user_username(token: str = Depends(oauth2_scheme)):
    """
    Валидирует JWT токен и извлекает username.
    В продакшене здесь нужно загружать JWKS (публичные ключи) из Keycloak и проверять подпись.
    Для демо мы декодируем токен и доверяем ему, так как он пришел от фронтенда.
    """
    try:
        # Декодируем токен без проверки подписи (для упрощения демо внутри Docker сети)
        # Внимание: options={"verify_signature": False} только для демо!
        payload = jwt.get_unverified_claims(token)
        
        username = payload.get("preferred_username")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# --- Database ---
def get_clickhouse_client():
    return Client(host=CLICKHOUSE_HOST, user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD)

# --- Endpoints ---

@app.get("/reports", response_model=List[ReportItem])
def get_my_reports(username: str = Depends(get_current_user_username)):
    """
    Возвращает отчеты ТОЛЬКО для текущего авторизованного пользователя.
    Данные берутся из OLAP (ClickHouse).
    """
    client = get_clickhouse_client()
    
    # SQL запрос с фильтрацией по username (Row-Level Security на уровне приложения)
    query = """
        SELECT 
            toString(report_date) as report_date,
            client_name,
            avg_battery_level,
            total_steps,
            max_muscle_voltage,
            errors_count
        FROM report_user_daily_mart
        WHERE keycloak_username = %(username)s
        ORDER BY report_date DESC
    """
    
    try:
        result = client.execute(query, {'username': username})
        
        # Преобразуем результат в список словарей
        reports = []
        for row in result:
            reports.append({
                "report_date": row[0],
                "client_name": row[1],
                "avg_battery_level": row[2],
                "total_steps": row[3],
                "max_muscle_voltage": row[4],
                "errors_count": row[5]
            })
            
        return reports
        
    except Exception as e:
        print(f"Error querying ClickHouse: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
