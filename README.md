# BionicPRO - Architecture & Security

> Архитектурное решение для управления учётными данными с поддержкой PKCE

## 🚀 Быстрый старт

```bash
# Запуск приложения с PKCE
./test-pkce.sh
```

## 📁 Задания

### Task 1: Архитектура и PKCE ✅
**Директория:** [Task1/](./Task1/)

**Документация:**
- 📊 [Архитектурное решение](./Task1/README.md) - C4 диаграммы и описание
- 📊 [PKCE Flow](./Task1/pkce-flow.puml) - Диаграмма последовательности
- 📖 [PKCE Implementation](./Task1/PKCE_IMPLEMENTATION.md) - Детали реализации
- 🚀 [Quick Start](./Task1/QUICK_START.md) - Инструкции по запуску
- 📝 [Changes Summary](./Task1/CHANGES_SUMMARY.md) - Резюме изменений
- 🧪 [Test Script](./Task1/test-pkce.sh) - Автоматическое тестирование

**Реализовано:**
- ✅ C4 Container диаграмма архитектуры
- ✅ PKCE (S256) в Keycloak
- ✅ PKCE интеграция во frontend
- ✅ Полная документация

### Task 2: Reports Service (Java ETL & Analytics) ✅
**Директория:** [Task2/](./Task2/)

**Документация:**
- 📊 [Архитектура Reports Service](./Task2/arch/bionicpro_reports_c4_container.puml) - C4 Container
- 📖 [Полная документация](./Task2/README.md) - Java ETL, Reports API, Airflow
- 🗄️ [ClickHouse DDL](./Task2/olap/ddl/01_create_tables.sql) - Схемы данных
- 🐍 [Airflow DAG](./Task2/airflow/dags/reports_etl_dag.py) - Оркестрация ETL

**Реализовано:**
- ✅ Java ETL (Spring Batch) для обработки CRM и телеметрии
- ✅ Reports API (Spring Boot) с OAuth2 защитой
- ✅ ClickHouse OLAP витрина данных
- ✅ Apache Airflow для оркестрации
- ✅ Spring Security + Keycloak интеграция
- ✅ Docker Compose для всех сервисов

### Task 3: _(планируется)_

## 🔄 Структура проекта

```
architecture-bionicpro/
├── Task1/                          # ✅ Задание 1 (PKCE Security)
│   ├── diagram.puml               # C4 Container диаграмма
│   ├── pkce-flow.puml             # PKCE последовательность
│   ├── README.md                  # Архитектурная документация
│   ├── PKCE_IMPLEMENTATION.md     # Реализация PKCE
│   ├── QUICK_START.md             # Быстрый старт
│   ├── CHANGES_SUMMARY.md         # Резюме изменений
│   └── test-pkce.sh               # Скрипт тестирования
├── Task2/                          # ✅ Задание 2 (Reports Service)
│   ├── arch/                      # Архитектурные диаграммы
│   ├── etl-java/                  # Java ETL (Spring Batch)
│   ├── reports-api/               # Reports API (Spring Boot)
│   ├── airflow/                   # Airflow оркестрация
│   ├── olap/                      # ClickHouse DDL/seed
│   ├── docker-compose.yml         # Полный стек сервисов
│   └── README.md                  # Документация Task2
├── Task3/                          # 🔄 Задание 3 (планируется)
├── frontend/                       # React + PKCE
│   ├── src/App.tsx                # PKCE конфигурация
│   └── public/silent-check-sso.html
├── keycloak/
│   └── realm-export.json          # PKCE включен
├── docker-compose.yaml             # Инфраструктура (Task1)
├── test-pkce.sh                    # Wrapper для Task1 скрипта
└── README.md                       # Этот файл
```

## 📊 Сервисы

| Сервис | URL | Учетные данные |
|--------|-----|----------------|
| Frontend | http://localhost:3000 | - |
| Keycloak Admin | http://localhost:8080 | admin / admin |
| PostgreSQL | localhost:5433 | keycloak_user / keycloak_password |

## 🛠️ Технологии

- **Keycloak 21.1** - Identity Provider
- **React 18 + TypeScript** - Frontend  
- **Keycloak-JS** - PKCE Support
- **Docker Compose** - Инфраструктура
- **PlantUML** - Диаграммы C4

## 📚 Полезные ссылки

- [RFC 7636 - PKCE](https://datatracker.ietf.org/doc/html/rfc7636)
- [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-09)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [C4 Model](https://c4model.com/)
