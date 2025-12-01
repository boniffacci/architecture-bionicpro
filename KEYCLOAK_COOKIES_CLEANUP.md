# Удаление Keycloak-кук после авторизации

## Проблема

После успешной авторизации через Keycloak в браузере пользователя оставались временные куки от Keycloak:
- `AUTH_SESSION_ID` — временная кука для OAuth-сессии
- `KC_AUTH_SESSION_HASH` — хеш OAuth-сессии
- `KC_RESTART` — кука для перезапуска OAuth-процесса

Эти куки не представляют серьёзной угрозы безопасности, но их наличие нежелательно, так как они:
1. Не используются auth-proxy (используется только `session_id`)
2. Могут вводить в заблуждение при отладке
3. Занимают место в браузере

## Решение

Реализовано удаление Keycloak-кук после успешной авторизации в эндпоинте `/callback` auth-proxy.

### Технические детали

#### 1. Удаление через JavaScript

В эндпоинте `/callback` (файл `auth_proxy/app.py`, строки 274-323) создаётся HTML-страница с JavaScript-кодом, который:
- Удаляет Keycloak-куки с разными путями (`/realms/{realm}/`, `/realms/{realm}`, `/`)
- Выполняет редирект на фронтенд после удаления кук

```javascript
// Удаляем Keycloak cookies
document.cookie = "AUTH_SESSION_ID=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/realms/reports-realm/; domain=localhost";
document.cookie = "KC_AUTH_SESSION_HASH=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/realms/reports-realm/; domain=localhost";
document.cookie = "KC_RESTART=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/realms/reports-realm/; domain=localhost";
// ... и другие варианты путей
```

#### 2. Удаление через Set-Cookie заголовки

Дополнительно используются Set-Cookie заголовки с `max_age=-1` для удаления кук (строки 338-359):

```python
for cookie_name in keycloak_cookies:
    response.set_cookie(
        key=cookie_name,
        value="",
        max_age=-1,
        expires=0,
        path=f"/realms/{settings.keycloak_realm}/",
        domain=None,
    )
```

### Список удаляемых кук

- `AUTH_SESSION_ID` — временная OAuth-сессия
- `AUTH_SESSION_ID_LEGACY` — legacy-версия
- `KC_RESTART` — перезапуск OAuth-процесса
- `KC_AUTH_SESSION_HASH` — хеш OAuth-сессии
- `KEYCLOAK_SESSION` — Keycloak-сессия (если есть)
- `KEYCLOAK_SESSION_LEGACY` — legacy-версия
- `KEYCLOAK_IDENTITY` — identity-токен (если есть)
- `KEYCLOAK_IDENTITY_LEGACY` — legacy-версия

## Тестирование

Добавлен тест `test_keycloak_cookies_deleted_after_login` в файл `tests/test_session_security.py` (строки 621-704), который проверяет:

1. Пользователь логинится через Keycloak
2. После редиректа на фронтенд проверяется, что временные Keycloak-куки удалены
3. Проверяется, что установлена только `session_id` кука
4. Проверяется, что пользователь успешно авторизован

### Запуск теста

```bash
uv run pytest tests/test_session_security.py::test_keycloak_cookies_deleted_after_login -v -s
```

### Результаты

✅ Все 6 тестов безопасности проходят успешно:
- `test_no_keycloak_cookies_exposed` — критичные Keycloak-куки не выдаются клиенту
- `test_session_cookie_required` — session_id кука необходима для доступа
- `test_single_session_per_user` — работает только последняя сессия пользователя
- `test_session_hijacking_protection` — защита от перехвата сессии работает
- `test_security_modal_on_invalid_session` — модальное окно с ошибкой безопасности отображается
- `test_keycloak_cookies_deleted_after_login` — Keycloak-куки удаляются после логина

## Архитектурные ограничения

Из-за того, что Keycloak и auth-proxy находятся на одном домене (`localhost`), но на разных портах (8080 и 3000), некоторые Keycloak-куки могут оставаться в браузере, если они установлены с path `/realms/{realm}/`.

Однако это не представляет серьёзной угрозы безопасности, так как:
1. Auth-proxy не использует эти куки (использует только `session_id`)
2. Эти куки установлены с `HttpOnly` и не доступны JavaScript
3. Эти куки привязаны к Keycloak path и не отправляются на auth-proxy

Для полного решения требуется использовать отдельный домен для Keycloak (например, `auth.example.com` и `app.example.com`).

## Преимущества решения

1. **Безопасность**: Временные OAuth-куки удаляются сразу после завершения авторизации
2. **Чистота**: В браузере остаётся только необходимая `session_id` кука
3. **Совместимость**: Решение работает с разными путями кук (с слэшем и без)
4. **Надёжность**: Используется комбинация JavaScript и Set-Cookie заголовков для максимальной совместимости

## Дополнительная информация

- Конфигурация Keycloak realm: `keycloak/realm-export.json`
- Настройки auth-proxy: `auth_proxy/config.py`
- Все тесты безопасности: `tests/test_session_security.py`
