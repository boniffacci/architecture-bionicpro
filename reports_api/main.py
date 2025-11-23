"""Основной модуль API для отчетов с проверкой JWT-токенов Keycloak."""

# Импортируем модуль json для сериализации словарей в строки
import json
# Импортируем модуль logging для вывода диагностических сообщений
import logging
# Импортируем типы Any и Dict для аннотаций типов функций
from datetime import datetime
from typing import Any, Dict, List, Optional

# Импортируем httpx для выполнения HTTP-запросов к Keycloak
import httpx
# Импортируем Depends, FastAPI, Header и HTTPException для построения API
from fastapi import Depends, FastAPI, Header, HTTPException
# Импортируем CORSMiddleware для настройки CORS-политики
from fastapi.middleware.cors import CORSMiddleware
# Импортируем Pydantic для валидации данных
from pydantic import BaseModel, Field
# Импортируем библиотеку PyJWT для работы с JWT-токенами
import jwt
# Импортируем RSAAlgorithm для преобразования открытых ключей из JWK в формат RSA
from jwt.algorithms import RSAAlgorithm
# Импортируем набор исключений PyJWT для обработки ошибок проверки токена
from jwt import exceptions as jwt_exceptions
# Импортируем ClickHouse клиент
import clickhouse_connect
# Импортируем MinIO клиент для хранения отчетов
from minio import Minio
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
from datetime import timedelta
import io
# Импортируем contextlib для lifespan
from contextlib import asynccontextmanager

# Настраиваем базовый уровень логирования на INFO
logging.basicConfig(level=logging.INFO)

# Глобальная переменная для MinIO-клиента
minio_client: Minio | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager для инициализации и очистки ресурсов."""
    # Startup: инициализация MinIO
    logging.info("Инициализация MinIO-клиента...")
    init_minio()
    logging.info("MinIO-клиент успешно инициализирован")
    
    # Startup: инициализация схемы debezium в ClickHouse
    logging.info("Инициализация схемы debezium в ClickHouse...")
    init_debezium_schema()
    logging.info("Схема debezium успешно инициализирована")
    
    yield
    
    # Shutdown: очистка ресурсов (если необходимо)
    logging.info("Завершение работы приложения")


# Создаем экземпляр FastAPI с lifespan
app = FastAPI(lifespan=lifespan)

# Добавляем промежуточное ПО для поддержки CORS-запросов с фронтенда
app.add_middleware(
    # Указываем класс промежуточного ПО, который добавляем
    CORSMiddleware,
    # Определяем список доменов, которым разрешен доступ к API
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "*"
    ],
    # Разрешаем передачу cookies и авторизационных заголовков
    allow_credentials=True,
    # Разрешаем все HTTP-методы для запросов
    allow_methods=["*"],
    # Разрешаем любые заголовки в запросах
    allow_headers=["*"],
)


def get_minio_client():
    """Получает глобальный MinIO-клиент."""
    global minio_client
    if minio_client is None:
        raise RuntimeError("MinIO-клиент не инициализирован")
    return minio_client


def init_minio():
    """Инициализирует MinIO-клиент и создает бакет reports с настройкой времени жизни файлов."""
    global minio_client
    
    # Создаем MinIO-клиент с учетом креденшиалов из docker-compose
    minio_client = Minio(
        "localhost:9000",  # Адрес MinIO-сервера
        access_key="minio_user",  # Логин из docker-compose
        secret_key="minio_password",  # Пароль из docker-compose
        secure=False  # Используем HTTP, а не HTTPS
    )
    
    bucket_name = "reports"
    
    # Проверяем, существует ли бакет
    if not minio_client.bucket_exists(bucket_name):
        logging.info(f"Бакет {bucket_name} не найден, создаем...")
        # Создаем бакет
        minio_client.make_bucket(bucket_name)
        logging.info(f"Бакет {bucket_name} успешно создан")
    else:
        logging.info(f"Бакет {bucket_name} уже существует")
    
    # Настраиваем lifecycle policy для автоматического удаления файлов через 92 дня
    try:
        lifecycle_config = LifecycleConfig(
            [
                Rule(
                    rule_id="expire-reports",  # ID правила
                    status="Enabled",  # Правило активно
                    expiration=Expiration(days=92),  # Удалять файлы через 92 дня
                )
            ]
        )
        minio_client.set_bucket_lifecycle(bucket_name, lifecycle_config)
        logging.info(f"Lifecycle policy для бакета {bucket_name} установлена: файлы будут удаляться через 92 дня")
    except Exception as e:
        logging.warning(f"Не удалось установить lifecycle policy: {e}")


def init_debezium_schema():
    """Инициализирует схему debezium в ClickHouse с Kafka Engine таблицами."""
    client = get_clickhouse_client()
    
    # Создаем базу данных debezium, если её нет
    logging.info("Проверка наличия базы данных debezium...")
    client.command("CREATE DATABASE IF NOT EXISTS debezium")
    logging.info("✓ База данных debezium создана или уже существует")
    
    # Проверяем, существуют ли таблицы
    existing_tables = client.query("SHOW TABLES FROM debezium").result_rows
    existing_table_names = {row[0] for row in existing_tables}
    
    # Создаем Kafka Engine таблицу для users, если её нет
    if 'users_kafka' not in existing_table_names:
        logging.info("Создание Kafka Engine таблицы для users...")
        client.command("""
            CREATE TABLE debezium.users_kafka (
                payload String
            ) ENGINE = Kafka
            SETTINGS
                kafka_broker_list = 'kafka:9092',
                kafka_topic_list = 'crm.public.users',
                kafka_group_name = 'clickhouse_crm_consumer',
                kafka_format = 'JSONAsString',
                kafka_num_consumers = 1,
                kafka_thread_per_consumer = 1,
                kafka_skip_broken_messages = 1000,
                kafka_max_block_size = 1048576
        """)
        logging.info("✓ Kafka Engine таблица users_kafka создана")
    else:
        logging.info("✓ Kafka Engine таблица users_kafka уже существует")
    
    # Создаем Join таблицу для users, если её нет
    if 'users' not in existing_table_names:
        logging.info("Создание Join таблицы для users...")
        client.command("""
            CREATE TABLE debezium.users (
                user_id Int32,
                user_uuid String,
                name String,
                email String,
                age Nullable(Int32),
                gender Nullable(String),
                country Nullable(String),
                address Nullable(String),
                phone Nullable(String),
                registered_at DateTime
            ) ENGINE = Join(ANY, LEFT, user_id)
        """)
        logging.info("✓ Join таблица users создана")
    else:
        logging.info("✓ Join таблица users уже существует")
    
    # Создаем Materialized View для users, если её нет
    if 'users_mv' not in existing_table_names:
        logging.info("Создание Materialized View для users...")
        client.command("""
            CREATE MATERIALIZED VIEW debezium.users_mv TO debezium.users AS
            SELECT
                JSONExtractInt(JSONExtractString(payload, 'after'), 'id') AS user_id,
                JSONExtractString(JSONExtractString(payload, 'after'), 'user_uuid') AS user_uuid,
                JSONExtractString(JSONExtractString(payload, 'after'), 'name') AS name,
                JSONExtractString(JSONExtractString(payload, 'after'), 'email') AS email,
                JSONExtractInt(JSONExtractString(payload, 'after'), 'age') AS age,
                JSONExtractString(JSONExtractString(payload, 'after'), 'gender') AS gender,
                JSONExtractString(JSONExtractString(payload, 'after'), 'country') AS country,
                JSONExtractString(JSONExtractString(payload, 'after'), 'address') AS address,
                JSONExtractString(JSONExtractString(payload, 'after'), 'phone') AS phone,
                fromUnixTimestamp64Micro(JSONExtractInt(JSONExtractString(payload, 'after'), 'registered_at')) AS registered_at
            FROM debezium.users_kafka
            WHERE JSONExtractString(payload, 'op') IN ('c', 'u', 'r')
        """)
        logging.info("✓ Materialized View users_mv создана")
    else:
        logging.info("✓ Materialized View users_mv уже существует")
    
    # Создаем Kafka Engine таблицу для telemetry_events, если её нет
    if 'telemetry_events_kafka' not in existing_table_names:
        logging.info("Создание Kafka Engine таблицы для telemetry_events...")
        client.command("""
            CREATE TABLE debezium.telemetry_events_kafka (
                payload String
            ) ENGINE = Kafka
            SETTINGS
                kafka_broker_list = 'kafka:9092',
                kafka_topic_list = 'telemetry.public.telemetry_events',
                kafka_group_name = 'clickhouse_telemetry_consumer',
                kafka_format = 'JSONAsString',
                kafka_num_consumers = 1,
                kafka_thread_per_consumer = 1,
                kafka_skip_broken_messages = 1000,
                kafka_max_block_size = 1048576
        """)
        logging.info("✓ Kafka Engine таблица telemetry_events_kafka создана")
    else:
        logging.info("✓ Kafka Engine таблица telemetry_events_kafka уже существует")
    
    # Создаем ReplacingMergeTree таблицу для telemetry_events, если её нет
    if 'telemetry_events' not in existing_table_names:
        logging.info("Создание ReplacingMergeTree таблицы для telemetry_events...")
        client.command("""
            CREATE TABLE debezium.telemetry_events (
                id Int64,
                event_uuid String,
                user_id Int32,
                prosthesis_type String,
                muscle_group String,
                signal_frequency Int32,
                signal_duration Int32,
                signal_amplitude Float64,
                created_ts DateTime,
                saved_ts DateTime
            ) ENGINE = ReplacingMergeTree(saved_ts)
            PARTITION BY (toYear(created_ts), toMonth(created_ts))
            ORDER BY (event_uuid, user_id, created_ts)
        """)
        logging.info("✓ ReplacingMergeTree таблица telemetry_events создана")
    else:
        logging.info("✓ ReplacingMergeTree таблица telemetry_events уже существует")
    
    # Создаем Materialized View для telemetry_events, если её нет
    if 'telemetry_events_mv' not in existing_table_names:
        logging.info("Создание Materialized View для telemetry_events...")
        client.command("""
            CREATE MATERIALIZED VIEW debezium.telemetry_events_mv TO debezium.telemetry_events AS
            SELECT
                JSONExtractInt(JSONExtractString(payload, 'after'), 'id') AS id,
                JSONExtractString(JSONExtractString(payload, 'after'), 'event_uuid') AS event_uuid,
                JSONExtractInt(JSONExtractString(payload, 'after'), 'user_id') AS user_id,
                JSONExtractString(JSONExtractString(payload, 'after'), 'prosthesis_type') AS prosthesis_type,
                JSONExtractString(JSONExtractString(payload, 'after'), 'muscle_group') AS muscle_group,
                JSONExtractInt(JSONExtractString(payload, 'after'), 'signal_frequency') AS signal_frequency,
                JSONExtractInt(JSONExtractString(payload, 'after'), 'signal_duration') AS signal_duration,
                JSONExtractFloat(JSONExtractString(payload, 'after'), 'signal_amplitude') AS signal_amplitude,
                fromUnixTimestamp64Micro(JSONExtractInt(JSONExtractString(payload, 'after'), 'created_ts')) AS created_ts,
                fromUnixTimestamp64Micro(JSONExtractInt(JSONExtractString(payload, 'after'), 'saved_ts')) AS saved_ts
            FROM debezium.telemetry_events_kafka
            WHERE JSONExtractString(payload, 'op') IN ('c', 'u', 'r')
        """)
        logging.info("✓ Materialized View telemetry_events_mv создана")
    else:
        logging.info("✓ Materialized View telemetry_events_mv уже существует")
    
    logging.info("✓ Схема debezium полностью инициализирована")


# Определяем класс конфигурации для параметров Keycloak
class KeycloakConfig:
    # Указываем адрес издателя токенов (realm) в Keycloak
    issuer: str = "http://localhost:8080/realms/reports-realm"
    # Формируем URL для получения открытых ключей (JWKS) Keycloak
    jwks_url: str = f"{issuer}/protocol/openid-connect/certs"
    # Указываем ожидаемую аудиторию (client_id) токена для backend-а
    audience: str | None = "reports-api"
    # Указываем допустимые алгоритмы подписи токена
    algorithms: tuple[str, ...] = ("RS256",)


# Определяем асинхронную функцию для получения JWKS с сервера Keycloak
async def get_jwks() -> Dict[str, Any]:
    # Создаем асинхронный HTTP-клиент с таймаутом в 5 секунд
    async with httpx.AsyncClient(timeout=5) as client:
        # Выполняем GET-запрос на получение набора ключей
        response = await client.get(KeycloakConfig.jwks_url)
        # Бросаем исключение, если Keycloak вернул ошибку
        response.raise_for_status()
        # Возвращаем тело ответа в виде словаря
        return response.json()


# Определяем зависимость FastAPI для проверки JWT-токена в заголовке Authorization
async def verify_jwt(
    authorization: str = Header(default=None),
    jwks: Dict[str, Any] = Depends(get_jwks),
) -> Dict[str, Any]:
    # Проверяем, что заголовок Authorization присутствует и содержит схему Bearer
    if not authorization or not authorization.lower().startswith("bearer "):
        # Возвращаем ошибку 401, если токен отсутствует
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    # Извлекаем сам токен из заголовка Authorization
    token = authorization.split(" ", 1)[1]
    # Пытаемся получить заголовок токена без проверки подписи
    try:
        header = jwt.get_unverified_header(token)
    # Обрабатываем любые ошибки парсинга заголовка токена
    except jwt_exceptions.PyJWTError as exc:
        # Возвращаем ошибку 401, если заголовок токена некорректен
        raise HTTPException(status_code=401, detail="Invalid token header") from exc

    logging.info("Token header kid: %s", header.get("kid"))

    # Ищем подходящий ключ в JWKS по идентификатору ключа (kid)
    key_dict = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
    # Проверяем, что ключ найден
    if not key_dict:
        # Возвращаем ошибку 401, если публичный ключ не найден
        logging.error("Public key not found for kid: %s", header.get("kid"))
        raise HTTPException(status_code=401, detail="Token signature key not found")

    logging.info("Key found for kid: %s", header.get("kid"))

    # Преобразуем найденный JWK в объект RSA-ключа
    public_key = RSAAlgorithm.from_jwk(json.dumps(key_dict))

    # Пытаемся декодировать и проверить токен с использованием публичного ключа
    try:
        logging.info("Decoding token with issuer=%s", KeycloakConfig.issuer)
        # Получаем payload без проверки для диагностики
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        logging.info("Token payload audience: %s", unverified_payload.get("aud"))
        logging.info("Token payload issuer: %s", unverified_payload.get("iss"))
        logging.info("Token payload azp (authorized party): %s", unverified_payload.get("azp"))

        # Декодируем токен БЕЗ проверки audience, так как публичный клиент reports-frontend
        # не включает audience в токен по умолчанию
        payload = jwt.decode(
            token,
            public_key,
            algorithms=list(KeycloakConfig.algorithms),
            # Не проверяем audience для публичных клиентов
            options={"verify_aud": False},
            issuer=KeycloakConfig.issuer,
        )
        logging.info("Token decoded successfully")
        
        # Дополнительная проверка: токен должен быть выдан для reports-frontend
        if payload.get("azp") not in ["reports-frontend", "reports-api"]:
            logging.error("Token not issued for expected client. azp=%s", payload.get("azp"))
            raise HTTPException(status_code=401, detail="Token not issued for this application")
    # Обрабатываем ошибку истечения срока действия токена
    except jwt_exceptions.ExpiredSignatureError as exc:
        # Возвращаем ошибку 401 при просроченном токене
        logging.error("Token expired: %s", exc)
        raise HTTPException(status_code=401, detail="Token expired") from exc
    # Обрабатываем ошибки, связанные с аудиториями или издателем токена
    except (jwt_exceptions.InvalidAudienceError, jwt_exceptions.InvalidIssuerError) as exc:
        # Возвращаем ошибку 401 при неверных параметрах токена
        logging.error("Invalid token claims: %s", exc)
        logging.error("Token issuer from token: %s", jwt.decode(token, options={"verify_signature": False}).get("iss"))
        logging.error("Expected issuer: %s", KeycloakConfig.issuer)
        raise HTTPException(status_code=401, detail="Invalid token claims") from exc
    # Обрабатываем любые другие ошибки валидации токена
    except jwt_exceptions.PyJWTError as exc:
        # Возвращаем ошибку 401, если токен некорректен по другим причинам
        logging.error("Invalid token: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    # Возвращаем полезную нагрузку токена, если проверка успешно прошла
    return payload


# Описываем маршрут GET /reports, который требует валидный JWT
@app.get("/reports")
async def get_reports(payload: Dict[str, Any] = Depends(verify_jwt)) -> Dict[str, Any]:
    # Логируем полезную нагрузку токена в формате JSON
    logging.info("JWT payload: %s", json.dumps(payload))
    # Возвращаем полезную нагрузку в ответе API
    return {"payload": payload}


# Описываем маршрут GET /jwt, который возвращает содержимое JWT токена
@app.get("/jwt")
async def get_jwt(authorization: str = Header(default=None)) -> Dict[str, Any]:
    # Проверяем наличие заголовка Authorization
    if not authorization:
        # Если заголовок отсутствует, возвращаем null
        return {"jwt": None}
    
    # Проверяем, что заголовок содержит схему Bearer
    if not authorization.lower().startswith("bearer "):
        # Если схема неверная, возвращаем null
        return {"jwt": None}
    
    # Извлекаем токен из заголовка
    token = authorization.split(" ", 1)[1]
    
    # Пытаемся декодировать токен без проверки подписи (для отображения содержимого)
    try:
        # Декодируем токен без проверки подписи
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Возвращаем содержимое токена
        return {"jwt": payload}
    except jwt_exceptions.PyJWTError as exc:
        # Если токен некорректен, возвращаем ошибку
        logging.error("Failed to decode JWT: %s", exc)
        return {"jwt": None, "error": str(exc)}


# ===== Модели данных для эндпоинта /report =====

class ReportRequest(BaseModel):
    """Модель запроса для генерации отчета."""
    user_id: int = Field(description="ID пользователя")
    start_ts: Optional[datetime] = Field(default=None, description="Начало отчетного периода")
    end_ts: Optional[datetime] = Field(default=None, description="Конец отчетного периода")
    schema: str = Field(default="default", description="Схема для чтения данных: 'default' или 'debezium'")


class ProsthesisStats(BaseModel):
    """Статистика по одному протезу."""
    prosthesis_type: str = Field(description="Тип протеза")
    events_count: int = Field(description="Количество событий")
    total_duration: int = Field(description="Общая длительность сигналов (мс)")
    avg_amplitude: float = Field(description="Средняя амплитуда сигнала")
    avg_frequency: float = Field(description="Средняя частота сигнала (Гц)")


class ReportResponse(BaseModel):
    """Модель ответа с отчетом по пользователю."""
    user_name: str = Field(description="Имя пользователя")
    user_email: str = Field(description="Email пользователя")
    total_events: int = Field(description="Всего событий за период")
    total_duration: int = Field(description="Общая длительность сигналов (мс)")
    prosthesis_stats: List[ProsthesisStats] = Field(description="Статистика по каждому протезу")


def get_clickhouse_client():
    """Создает подключение к ClickHouse."""
    return clickhouse_connect.get_client(
        host='localhost',
        port=8123,
        username='default',
        password='clickhouse_password'
    )


@app.post("/report", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """
    Генерирует отчет по пользователю за указанный период с кешированием в MinIO.
    
    Args:
        request: Параметры запроса (user_id, start_ts, end_ts, schema)
        
    Returns:
        ReportResponse: Отчет с статистикой по пользователю
    """
    # Валидация параметра schema
    if request.schema not in ["default", "debezium"]:
        raise HTTPException(status_code=400, detail="Параметр schema должен быть 'default' или 'debezium'")
    
    minio = get_minio_client()
    bucket_name = "reports"
    
    # Формируем имя папки для пользователя с учетом схемы
    user_folder = f"{request.schema}/{request.user_id}"
    
    # Формируем имя файла на основе временных параметров
    if request.start_ts and request.end_ts:
        # Форматируем datetime в строку для имени файла (ISO 8601 без символов, несовместимых с именами файлов)
        start_str = request.start_ts.strftime("%Y-%m-%dT%H-%M-%S")
        end_str = request.end_ts.strftime("%Y-%m-%dT%H-%M-%S")
        file_name = f"{user_folder}/{start_str}__{end_str}.json"
    elif request.start_ts:
        start_str = request.start_ts.strftime("%Y-%m-%dT%H-%M-%S")
        file_name = f"{user_folder}/{start_str}__none.json"
    elif request.end_ts:
        end_str = request.end_ts.strftime("%Y-%m-%dT%H-%M-%S")
        file_name = f"{user_folder}/none__{end_str}.json"
    else:
        file_name = f"{user_folder}/all_time.json"
    
    # Проверяем, существует ли файл в MinIO
    try:
        response = minio.get_object(bucket_name, file_name)
        # Файл существует, загружаем его
        cached_data = json.loads(response.read().decode('utf-8'))
        response.close()
        response.release_conn()
        logging.info(f"Отчет загружен из кеша MinIO: {file_name}")
        return ReportResponse(**cached_data)
    except Exception as e:
        # Файл не существует или произошла ошибка при чтении
        logging.info(f"Отчет не найден в кеше MinIO ({file_name}), генерируем новый: {e}")
    
    # Генерируем отчет из ClickHouse
    client = get_clickhouse_client()
    
    # Определяем таблицы в зависимости от схемы
    if request.schema == "debezium":
        users_table = "debezium.users"
        telemetry_table = "debezium.telemetry_events"
        time_field = "created_ts"  # В debezium используется created_ts
    else:
        users_table = "users"
        telemetry_table = "telemetry_events"
        time_field = "signal_time"  # В default используется signal_time
    
    # Получаем информацию о пользователе
    user_query = f"""
    SELECT name, email
    FROM {users_table}
    WHERE user_id = {{user_id:Int32}}
    """
    
    user_result = client.query(user_query, parameters={'user_id': request.user_id})
    
    if not user_result.result_rows:
        raise HTTPException(status_code=404, detail=f"Пользователь с ID {request.user_id} не найден в схеме {request.schema}")
    
    user_name, user_email = user_result.result_rows[0]
    
    # Формируем запрос для общей статистики
    total_query = f"""
    SELECT 
        COUNT(*) as total_events,
        SUM(signal_duration) as total_duration
    FROM {telemetry_table}
    WHERE user_id = {{user_id:Int32}}
    """
    
    params = {'user_id': request.user_id}
    
    if request.start_ts:
        total_query += f" AND {time_field} >= {{start_ts:DateTime}}"
        params['start_ts'] = request.start_ts
    
    if request.end_ts:
        total_query += f" AND {time_field} < {{end_ts:DateTime}}"
        params['end_ts'] = request.end_ts
    
    total_result = client.query(total_query, parameters=params)
    total_events, total_duration = total_result.result_rows[0]
    
    # Если нет событий, возвращаем пустой отчет
    if total_events == 0:
        report = ReportResponse(
            user_name=user_name,
            user_email=user_email,
            total_events=0,
            total_duration=0,
            prosthesis_stats=[]
        )
    else:
        # Получаем статистику по каждому протезу
        prosthesis_query = f"""
        SELECT 
            prosthesis_type,
            COUNT(*) as events_count,
            SUM(signal_duration) as total_duration,
            AVG(signal_amplitude) as avg_amplitude,
            AVG(signal_frequency) as avg_frequency
        FROM {telemetry_table}
        WHERE user_id = {{user_id:Int32}}
        """
        
        if request.start_ts:
            prosthesis_query += f" AND {time_field} >= {{start_ts:DateTime}}"
        
        if request.end_ts:
            prosthesis_query += f" AND {time_field} < {{end_ts:DateTime}}"
        
        prosthesis_query += " GROUP BY prosthesis_type ORDER BY events_count DESC"
        
        prosthesis_result = client.query(prosthesis_query, parameters=params)
        
        # Формируем список статистики по протезам
        prosthesis_stats = []
        for prosthesis_type, events_count, duration, avg_amplitude, avg_frequency in prosthesis_result.result_rows:
            prosthesis_stats.append(ProsthesisStats(
                prosthesis_type=prosthesis_type,
                events_count=events_count,
                total_duration=int(duration),
                avg_amplitude=float(avg_amplitude),
                avg_frequency=float(avg_frequency)
            ))
        
        report = ReportResponse(
            user_name=user_name,
            user_email=user_email,
            total_events=total_events,
            total_duration=int(total_duration or 0),
            prosthesis_stats=prosthesis_stats
        )
    
    # Сохраняем отчет в MinIO
    try:
        report_json = report.model_dump_json(indent=2)
        report_bytes = report_json.encode('utf-8')
        
        minio.put_object(
            bucket_name,
            file_name,
            io.BytesIO(report_bytes),
            length=len(report_bytes),
            content_type='application/json'
        )
        logging.info(f"Отчет сохранен в MinIO: {file_name}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении отчета в MinIO: {e}")
    
    return report


# Запускаем приложение, если файл выполняется напрямую
if __name__ == "__main__":
    # Импортируем asyncio и uvicorn для запуска сервера
    import asyncio
    from uvicorn import Config, Server

    # Создаем конфигурацию сервера
    config = Config(app, host="0.0.0.0", port=3002)
    # Создаем экземпляр сервера
    server = Server(config)
    # Запускаем сервер с asyncio.run
    asyncio.run(server.serve())