# BionicPRO Reports Service

## Get Started

```bash
docker-compose up -d
```

Настроить подключение к базе данных в Airflow в ui http://localhost:8081 или скриптом:

```bash
docker exec architecture-bionicpro-airflow-scheduler-1 airflow connections add reports_postgres \
  --conn-type postgres \
  --conn-host reports_db \
  --conn-port 5432 \
  --conn-login reports_user \
  --conn-password reports_password \
  --conn-schema reports_db
```

## Сервисы

DAG запускается ежедневно в 2:00 по расписанию.

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Airflow UI**: http://localhost:8081 (Login: admin Password: admin)
- **Keycloak**: http://localhost:8080 (Login: admin Password: admin)

## Отчеты

- `GET /reports` - Получить все отчёты
- `GET /reports/customer/:customerId` - Получить отчёт по ID клиента
- `GET /reports/customer/:customerId/telemetry` - Получить телеметрию клиента
- `GET /reports/customer/:customerId/stats` - Получить статистику клиента
