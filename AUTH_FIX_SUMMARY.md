# Исправление ошибки авторизации и настройка валидации JWT

## Проблема

При входе через Keycloak пользователь перенаправлялся на `http://localhost:3000/?error=invalid_token` с ошибкой **"Invalid issuer"**.

### Причина

JWT токен от Keycloak содержит `issuer` (iss) с внутренним Docker URL:
```
"iss": "http://keycloak:8080/realms/reports-realm"
```

Но `auth_proxy` и `reports_api` ожидали публичный URL:
```
"iss": "http://localhost:8080/realms/reports-realm"
```

## Решение

### 1. Исправлена проверка JWT в `auth_proxy`

**Файл:** `auth_proxy/keycloak_client.py`

Добавлена поддержка обоих вариантов issuer:
- Внутренний: `http://keycloak:8080/realms/reports-realm`
- Публичный: `http://localhost:8080/realms/reports-realm`

```python
# Пробуем оба варианта issuer (внутренний и публичный)
for issuer_url in [self.realm_url, self.public_realm_url]:
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=issuer_url,
            options={"verify_aud": False},
        )
        return payload
    except jwt.InvalidIssuerError:
        continue  # Пробуем следующий issuer
```

### 2. Исправлена проверка JWT в `reports_api`

**Файл:** `reports_api/main.py`

Добавлена поддержка нескольких вариантов issuer:

```python
possible_issuers = [
    KeycloakConfig.issuer,  # Внутренний URL
    "http://localhost:8080/realms/reports-realm",  # Публичный URL
]

for issuer in possible_issuers:
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=list(KeycloakConfig.algorithms),
            options={"verify_aud": False},
            issuer=issuer,
        )
        break
    except jwt_exceptions.InvalidIssuerError:
        continue
```

### 3. Добавлена настройка публичного URL Keycloak

**Файл:** `auth_proxy/config.py`

```python
keycloak_url: str = "http://localhost:8080"  # Внутренний URL (для server-to-server)
keycloak_public_url: str = "http://localhost:8080"  # Публичный URL (для браузера)
```

**Файл:** `docker-compose.yaml`

```yaml
AUTH_PROXY_KEYCLOAK_URL: http://keycloak:8080  # Внутренний URL
AUTH_PROXY_KEYCLOAK_PUBLIC_URL: http://localhost:8080  # Публичный URL
```

## Валидация JWT по публичному ключу Keycloak

### Публичные ключи Keycloak

Keycloak предоставляет публичные ключи через JWKS endpoint:
```
http://localhost:8080/realms/reports-realm/protocol/openid-connect/certs
```

Ответ содержит два ключа:
1. **RSA-OAEP** (use: "enc") - для шифрования
2. **RS256** (use: "sig") - для подписи JWT

### Проверка подписи JWT

И `auth_proxy`, и `reports_api` проверяют подпись JWT следующим образом:

1. Получают JWKS от Keycloak
2. Находят ключ по `kid` (key ID) из заголовка токена
3. Преобразуют JWK в RSA публичный ключ
4. Проверяют подпись токена с помощью `PyJWT`

```python
# Получаем JWKS
jwks = await get_jwks()

# Находим ключ по kid
kid = header.get("kid")
key_dict = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)

# Преобразуем JWK в RSA ключ
public_key = RSAAlgorithm.from_jwk(json.dumps(key_dict))

# Проверяем подпись
payload = jwt.decode(
    token,
    public_key,
    algorithms=["RS256"],
    issuer=issuer_url,
    options={"verify_aud": False},
)
```

## Тестирование

### 1. Проверка авторизации

1. Откройте http://localhost:3000/
2. Вы будете перенаправлены на Keycloak
3. Войдите с учётными данными: `admin` / `admin`
4. После успешного входа вы вернётесь на главную страницу
5. Должна отобразиться информация о пользователе

### 2. Проверка JWT токена

```bash
# Получить JWT токен (требуется авторизация)
curl -H "Authorization: Bearer <TOKEN>" http://localhost:3003/jwt
```

### 3. Проверка отчётов

```bash
# Создать отчёт (требуется авторизация)
curl -X POST http://localhost:3003/reports \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_ts": null,
    "end_ts": "2025-12-01T00:00:00Z",
    "schema": "default"
  }'
```

## Изменённые файлы

1. `auth_proxy/config.py` - добавлена настройка `keycloak_public_url`
2. `auth_proxy/keycloak_client.py` - поддержка нескольких issuer
3. `auth_proxy/app.py` - логирование auth_url
4. `reports_api/main.py` - поддержка нескольких issuer
5. `docker-compose.yaml` - добавлена переменная `AUTH_PROXY_KEYCLOAK_PUBLIC_URL`

## Статус

✅ Ошибка `invalid_token` исправлена
✅ Поддержка обоих вариантов issuer (внутренний и публичный)
✅ Валидация JWT по публичному ключу Keycloak
✅ Проверка подписи JWT в `auth_proxy` и `reports_api`
