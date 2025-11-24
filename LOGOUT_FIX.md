# Исправление ошибки logout в auth_proxy

## Проблема

При нажатии кнопки "Выйти" на `http://localhost:3000` пользователь не разлогинивался и редиректился обратно авторизованным.

### Ошибка 1 в логах

```
INFO:httpx:HTTP Request: POST http://keycloak:8080/realms/reports-realm/protocol/openid-connect/logout "HTTP/1.1 400 Bad Request"
WARNING:keycloak_client:Keycloak logout returned status 400: {"error":"invalid_grant","error_description":"Invalid token issuer. Expected 'http://keycloak:8080/realms/reports-realm'"}
WARNING:app:Failed to logout user prosthetic3 from Keycloak
```

### Ошибка 2 в логах (после первой попытки исправления)

```
ERROR:keycloak_client:Failed to logout from Keycloak: All connection attempts failed
WARNING:app:Failed to logout user prosthetic3 from Keycloak
```

### Причина

1. **Первая проблема**: Токены выдавались с issuer, основанным на URL запроса (из-за отсутствия настройки `KC_HOSTNAME_URL` в Keycloak). При обращении изнутри Docker-сети issuer был `http://keycloak:8080`, а при обращении из браузера - `http://localhost:8080`.

2. **Вторая проблема**: При попытке использовать публичный URL (`http://localhost:8080`) для logout из контейнера `auth-proxy`, он не мог подключиться, так как `localhost` внутри контейнера указывает на сам контейнер.

## Решение

### 1. Настройка Keycloak через переменные окружения

В `docker-compose.yaml` добавлены переменные окружения для Keycloak:

```yaml
environment:
  KC_HOSTNAME_URL: http://localhost:8080
  KC_HOSTNAME_ADMIN_URL: http://localhost:8080
  KC_HOSTNAME_STRICT: "false"
```

Это гарантирует, что Keycloak всегда будет использовать `http://localhost:8080` в качестве issuer в токенах, независимо от того, по какому URL к нему обращаются (внутреннему или публичному).

### 2. Использование внутреннего URL для logout endpoint

В `auth_proxy/keycloak_client.py` `logout_endpoint` использует внутренний URL:

```python
# logout_endpoint использует внутренний URL для HTTP-запроса
self.logout_endpoint = f"{self.realm_url}/protocol/openid-connect/logout"  # http://keycloak:8080/...
```

Это позволяет `auth-proxy` успешно подключиться к Keycloak изнутри Docker-сети, при этом issuer в токенах (`http://localhost:8080`) совпадает с настроенным `KC_HOSTNAME_URL`.

## Проверка

1. Пересоберите и перезапустите `auth-proxy`:
   ```bash
   docker compose build auth-proxy
   docker compose up -d auth-proxy
   ```

2. Откройте `http://localhost:3000` в браузере

3. Авторизуйтесь (например, как `prosthetic1:prosthetic123`)

4. Нажмите кнопку "Выйти"

5. Убедитесь, что:
   - Вас перенаправляет на страницу входа Keycloak
   - Вы больше не авторизованы (нужно снова вводить логин/пароль)
   - В логах `auth-proxy` нет ошибок 400

### Ожидаемые логи после исправления

```
INFO:httpx:HTTP Request: POST http://localhost:8080/realms/reports-realm/protocol/openid-connect/logout "HTTP/1.1 204 No Content"
INFO:keycloak_client:Keycloak session terminated successfully
INFO:app:User prosthetic1 logged out from Keycloak
INFO:app:User prosthetic1 signed out (local session deleted)
```

## Технические детали

### Почему важно использовать правильный URL для logout

1. **Token Issuer Validation**: Keycloak проверяет, что issuer в токене совпадает с realm URL, используемым для logout
2. **Security**: Это предотвращает использование токенов от одного realm для logout в другом
3. **Multi-tenant**: В multi-tenant окружениях важно, чтобы токены и logout endpoints соответствовали друг другу

### Какие endpoints используют какие URLs

| Endpoint | URL Type | Причина |
|----------|----------|---------|
| Authorization (auth) | Публичный (localhost:8080) | Браузер пользователя делает редирект |
| Token exchange | Внутренний (keycloak:8080) | Server-to-server запрос |
| Userinfo | Внутренний (keycloak:8080) | Server-to-server запрос |
| JWKS (публичные ключи) | Внутренний (keycloak:8080) | Server-to-server запрос |
| **Logout** | **Публичный (localhost:8080)** | Токены выданы с публичным issuer |

## Связанные файлы

- `auth_proxy/keycloak_client.py` - исправлен logout_endpoint
- `auth_proxy/config.py` - настройки публичного и внутреннего URLs
- `docker-compose.yaml` - переменные окружения для auth-proxy
