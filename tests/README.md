# E2E Тесты для веб-приложения с Keycloak

## Описание

Набор End-to-End тестов для проверки работы веб-приложения с авторизацией через Keycloak.
Тесты написаны на Python с использованием pytest и Playwright.

## Структура тестов

### `conftest.py`
Конфигурация pytest с фикстурами для:
- Запуска браузера Playwright (Chromium в headless режиме)
- Создания изолированных контекстов браузера для каждого теста
- Настройки URL фронтенда и бэкенда
- Тестовых учетных данных пользователя

### `test_e2e_keycloak.py`
Основной файл с E2E тестами, включающий:

#### 1. **TestServiceAvailability** - Тесты доступности сервисов
- `test_frontend_responds` - Проверка доступности фронтенда (localhost:5173)
- `test_backend_responds` - Проверка доступности бэкенда (localhost:3001)

#### 2. **TestKeycloakAuthentication** - Тесты авторизации через Keycloak
- `test_login_flow` - Полный процесс авторизации:
  - Открытие фронтенда
  - Автоматический редирект на Keycloak
  - Ввод учетных данных (user1/password123)
  - Редирект обратно на фронтенд
  - Проверка успешной авторизации
  - Проверка отображения контента

- `test_reports_button_shows_jwt` - Проверка JWT токена:
  - Авторизация пользователя
  - Нажатие на кнопку "Вызвать GET /reports"
  - Перехват HTTP запроса к бэкенду
  - Проверка наличия JWT токена в заголовке Authorization
  - Декодирование и проверка содержимого JWT payload

#### 3. **TestFullE2EFlow** - Полный E2E тест
- `test_complete_flow` - Комплексный тест всего процесса:
  - Проверка доступности фронтенда и бэкенда
  - Авторизация через Keycloak
  - Проверка отображения страницы
  - Проверка JWT токена в запросах к бэкенду

## Предварительные требования

### Запущенные сервисы
Перед запуском тестов должны быть запущены:
- **Фронтенд** на `localhost:5173`
- **Бэкенд** на `localhost:3001`
- **Keycloak** на `localhost:8080` с настроенным realm `reports-realm`

### Установка зависимостей

```bash
# Установка Python зависимостей через uv
uv pip install -e .

# Установка браузеров Playwright
source .venv/bin/activate
playwright install chromium
```

## Запуск тестов

### Запуск всех тестов
```bash
source .venv/bin/activate
pytest tests/test_e2e_keycloak.py -v -s
```

### Запуск конкретного класса тестов
```bash
# Только тесты доступности сервисов
pytest tests/test_e2e_keycloak.py::TestServiceAvailability -v -s

# Только тесты авторизации
pytest tests/test_e2e_keycloak.py::TestKeycloakAuthentication -v -s

# Полный E2E тест
pytest tests/test_e2e_keycloak.py::TestFullE2EFlow -v -s
```

### Запуск конкретного теста
```bash
pytest tests/test_e2e_keycloak.py::TestKeycloakAuthentication::test_login_flow -v -s
```

## Параметры запуска

- `-v` - verbose режим (подробный вывод)
- `-s` - показывать print() выводы в консоли
- `--headed` - запуск браузера в видимом режиме (не headless)

## Тестовые данные

### Пользователь для тестов
- **Username**: `user1`
- **Password**: `password123`

Эти учетные данные должны быть настроены в Keycloak realm `reports-realm`.

## Скриншоты

Тесты автоматически создают скриншоты в `/tmp/`:
- `/tmp/keycloak_after_login.png` - Страница после входа в Keycloak
- `/tmp/keycloak_auth_success.png` - Страница после успешной авторизации
- `/tmp/keycloak_reports_jwt.png` - Страница после вызова /reports
- `/tmp/keycloak_full_e2e.png` - Финальный скриншот полного E2E теста

## Проверяемые сценарии

### ✅ Проверка доступности
- Фронтенд отвечает на HTTP запросы (статус 200)
- Бэкенд отвечает на HTTP запросы (статус 404 с {"detail":"Not Found"})

### ✅ Авторизация через Keycloak
- Автоматический редирект на страницу входа Keycloak
- Ввод учетных данных и отправка формы
- Редирект обратно на фронтенд после успешной авторизации
- Отображение страницы с заголовком "✓ Вы авторизованы!"
- Наличие кнопки "Вызвать GET /reports"

### ✅ Проверка JWT токена
- JWT токен передается в заголовке Authorization
- Токен имеет формат "Bearer <token>"
- JWT токен имеет корректную структуру (3 части, разделенные точками)
- JWT payload содержит информацию о пользователе:
  - `sub` - идентификатор пользователя
  - `preferred_username` - имя пользователя
  - `email` - email пользователя
  - `realm_access.roles` - роли пользователя

## Отладка

Для отладки тестов используйте:

```bash
# Запуск в видимом режиме браузера (не headless)
# Отредактируйте conftest.py: headless: False

# Просмотр скриншотов
ls -lh /tmp/keycloak_*.png
```

## Возможные проблемы

### Тесты падают с timeout
- Убедитесь, что все сервисы запущены (фронтенд, бэкенд, Keycloak)
- Проверьте, что Keycloak полностью инициализирован
- Увеличьте timeout в тестах при необходимости

### Не находятся элементы на странице
- Проверьте скриншоты в `/tmp/`
- Убедитесь, что фронтенд использует правильные тексты кнопок и заголовков
- Проверьте, что React приложение полностью загрузилось

### JWT токен не передается
- Проверьте настройки CORS на бэкенде
- Убедитесь, что Keycloak правильно настроен для клиента `reports-frontend`
- Проверьте redirect URIs в настройках клиента Keycloak

## Результаты тестов

При успешном прохождении всех тестов вы увидите:

```
============================= test session starts ==============================
collected 5 items

tests/test_e2e_keycloak.py::TestServiceAvailability::test_frontend_responds PASSED
tests/test_e2e_keycloak.py::TestServiceAvailability::test_backend_responds PASSED
tests/test_e2e_keycloak.py::TestKeycloakAuthentication::test_login_flow PASSED
tests/test_e2e_keycloak.py::TestKeycloakAuthentication::test_reports_button_shows_jwt PASSED
tests/test_e2e_keycloak.py::TestFullE2EFlow::test_complete_flow PASSED

============================== 5 passed in XX.XXs ===============================
```

## Дополнительная информация

- Тесты используют изолированные контексты браузера для каждого теста
- Каждый тест независим и может выполняться отдельно
- Тесты автоматически очищают ресурсы после завершения
- Используется Chromium браузер из Playwright
