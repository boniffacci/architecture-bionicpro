# BionicPRO - Architecture & Security Implementation

## Задача 1. Предложите архитектурное решение и доработайте диаграмму C4 для управления учётными данными пользователя.
**Диаграмма**: [diagram.puml](./diagram.puml)
**Документация**: [README.md](./README.md)

## Задача 2.  Улучшите безопасность существующего приложения, заменив Code Grant на PKCE
### Запуск приложения:
docker-compose up -d
### Доступ к сервисам:

| Сервис | URL | Credentials |
|--------|-----|-------------|
| **Frontend** | http://localhost:3000 | - |
| **Keycloak Admin** | http://localhost:8080 | admin / admin |
| **Keycloak DB** | localhost:5433 | keycloak_user / keycloak_password |

*Доступные пользователи:**

| Username | Password | Role |
|----------|----------|------|
| prothetic1 | prothetic123 | prothetic_user |
| prothetic2 | prothetic123 | prothetic_user |
| admin1 | admin123 | administrator |
| user1 | password123 | user |
