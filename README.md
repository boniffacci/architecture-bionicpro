# BionicPRO Reports Service

## Get Started

```bash
docker-compose up -d
```

### Настроить подключение к базе данных в Airflow в ui http://localhost:8081 или скриптом:

```bash
docker exec architecture-bionicpro-airflow-scheduler-1 airflow connections add reports_postgres \
  --conn-type postgres \
  --conn-host reports_db \
  --conn-port 5432 \
  --conn-login reports_user \
  --conn-password reports_password \
  --conn-schema reports_db
```

### Настройка Keycloak

```bash
# Создать пользователей и назначить роли
./setup_keycloak.sh
```

**Тестовые пользователи для входа:**

- `ivan.petrov@email.com` / `password123`
- `maria.sidorova@email.com` / `password123`
- `alexey.kozlov@email.com` / `password123`
- `elena.volkova@email.com` / `password123`
- `dmitry.novikov@email.com` / `password123`

## Сервисы

DAG запускается ежедневно в 2:00 по расписанию.

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Airflow UI**: http://localhost:8081 (Login: admin Password: admin)
- **Keycloak**: http://localhost:8080 (Login: admin Password: admin)

## API Эндпоинты

- `GET /reports` - Получить свои отчёты (требует Keycloak токен)
- `GET /reports/customer/:customerId` - Получить отчёт по ID клиента (только свои данные)
- `GET /reports/customer/:customerId/telemetry` - Получить телеметрию клиента (только свои данные)
- `GET /reports/customer/:customerId/stats` - Получить статистику клиента (только свои данные)
