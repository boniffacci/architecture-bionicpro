## Задание 1. Повышение безопасности системы

### Архитектурное решение для управления учётными данными пользователя

Внутри системы BionicPRO добавляем IdP Keycloak. Данный сервис будет служить как SSO для всех приложений системы (CRM, интернет-магазин, API). Реализуем Federated Identity, который позволяет настроить доступы для сотрудников из разных стран (одно из требований бизнеса). Keycloak поддерживает федерализацию.

Для исключения передачи access и refresh токенов на фронтенд (одно из требований бизнеса) предлагается воспользоваться паттерном BFF (Backend For Frontend). Токены будут храниться на "промежуточном" бэкенде, который будет осуществлять все взаимодействие с Keycloak. На фронтенд будет приходить только сессионная Http-Only cookie, которую BFF будет разменивать на access_token. BFF будет обновлять access_token по refresh_token, который также будет храниться на сервере. Время жизни access_token - 5 минут.

Также рекомендуется настроить RBAC (Role-Based Access Control) для разделения доступов к данным на основе ролей.

![to-be.jpg](to-be.jpg)

### Улучшите безопасность существующего приложения, заменив Code Grant на PKCE

Для того, чтобы включить PKCE в Keycloak, необходимо проделать следующие шаги:
1. Поднять сервисы через docker-compose: `docker compose -f docker-compose.yaml up`
2. Перейти в админку Keycloak: http://localhost:8080
3. Ввести логин/пароль администратора (KEYCLOAK_ADMIN указан в файле docker-compose.yaml)
4. В боковом меню перейти в раздел Clients
5. В списке клиентов нажать на reports-frontend и открыть вкладку Advanced
6. В разделе Advanced Settings для настройки Proof Key for Code Exchange Code Challenge Method выставить значение S256, нажать Save
7. Далее можно экспортировать конфигурацию realm в виде файла realm-export.json. В боковом меню перейти в раздел Realm Settings. В правом верхнем углу в выпадающем списке Actions выбрать Partial Export. Поставить Include Clients - On, нажать Export.

Отредактируем файл `frontend\src\App.tsx`. Добавим строки:

```
const initOptions = {
  pkceMethod: 'S256'
};
```

Изменим инициализацию компонента ReactKeycloakProvider:

`<ReactKeycloakProvider authClient={keycloak} initOptions={initOptions}>`