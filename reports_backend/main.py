"""Основной модуль API для отчетов с проверкой JWT-токенов Keycloak."""

# Импортируем модуль json для сериализации словарей в строки
import json
# Импортируем модуль logging для вывода диагностических сообщений
import logging
# Импортируем типы Any и Dict для аннотаций типов функций
from typing import Any, Dict

# Импортируем httpx для выполнения HTTP-запросов к Keycloak
import httpx
# Импортируем Depends, FastAPI, Header и HTTPException для построения API
from fastapi import Depends, FastAPI, Header, HTTPException
# Импортируем CORSMiddleware для настройки CORS-политики
from fastapi.middleware.cors import CORSMiddleware
# Импортируем библиотеку PyJWT для работы с JWT-токенами
import jwt
# Импортируем RSAAlgorithm для преобразования открытых ключей из JWK в формат RSA
from jwt.algorithms import RSAAlgorithm
# Импортируем набор исключений PyJWT для обработки ошибок проверки токена
from jwt import exceptions as jwt_exceptions

# Настраиваем базовый уровень логирования на INFO
logging.basicConfig(level=logging.INFO)

# Создаем экземпляр FastAPI для определения маршрутов сервиса
app = FastAPI()

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


# Запускаем приложение, если файл выполняется напрямую
if __name__ == "__main__":
    # Импортируем asyncio и uvicorn для запуска сервера
    import asyncio
    from uvicorn import Config, Server

    # Создаем конфигурацию сервера
    config = Config(app, host="0.0.0.0", port=3001)
    # Создаем экземпляр сервера
    server = Server(config)
    # Запускаем сервер с asyncio.run
    asyncio.run(server.serve())