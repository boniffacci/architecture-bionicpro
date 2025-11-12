# architecture-bionicpro

## Постановка задачи
    
Нужно улучшить безопасность приложения, заменив Code Grant на PKCE. Затем необходимо подготовить API для работы с отчётом.  

1. **Реализовать PKCE.** Его нужно добавить к существующим приложениям — фронтенду и Keycloak. 
2. **Создать бэкенд-часть приложения для API.** Добавить API /reports в этот бэкенд для передачи отчётов. Тут не требуется поход в базы данных, нужно ограничется генерацией произвольных данных.

При проверке удостовериться, что:
- Бэкенд должен отдавать данные только пользователям с ролью prothetic_user.
- Бэкенд проверяет валидность подписи токена. Если валидация не прошла, он выдаёт ошибку 401.

## О проекте

**Цель:** предоставить протезированным пользователям доступ к данным о работе их протезов.

**Стек технологий:**
- Frontend: React + Tailwind + @react-keycloak/web
- Backend: FastAPI (Python 3.12)
- Auth: Keycloak 21 + PKCE
- Инфраструктура: Docker + Docker Compose

**Структура проекта:**   
   
- docker-compose.yaml 
- **API/**	
	+ Dockerfile
	+ main.py
	+ requirements.txt
- **keycloak/**
	+ realm-export.json
- **frontend/**
	+ Dockerfile
	+ ...
	+ **public/**
	+ **src/**
		* App.tsx 
		* ...
		* components/ReportPage.tsx 


### Аутентификация и авторизация

#### PKCE
- Включена в Keycloak через:
	- pkce.code.challenge.method: S256
	- publicClient: true
- Frontend использует библиотеку @react-keycloak/web с initOptions.pkceMethod = 'S256'
- Таким образом, frontend не использует client secret, но всё ещё безопасно инициирует авторизацию.

#### Проверка токена на бэкенде
В /reports выполняется:
- Загрузка сертификатов с /.well-known/openid-configuration
- Проверка подписи JWT через PyJWT
- Проверка aud === "reports-api"
- Проверка iss === "http://localhost:8080/realms/reports-realm"
- Проверка роли prothetic_user в realm_access.roles

### API: /reports
   
Назначение: предоставить список отчётов, связанных с устройствами текущего пользователя.

Гарантии:
- Каждый пользователь получает только свои устройства.
- Количество устройств — от 1 до 5, определяется детерминированно по user_id.
- Поля в отчёте:

    | Поле | Описание |
    |---|---|
    | device | UUID протеза |
    | reportId | Уникальный идентификатор отчёта |
    | value | Значение показателя работы протеза (20–95) |
    
### Интерфейс пользователя

Компонент ReportPage.tsx:
- Отображает кнопку загрузки отчёта.
- При ошибке (401 или 403) показывает сообщение пользователю.
- Показывает таблицу отчётов, если получены успешно.
- Добавлена кнопка "Logout" для выхода через Keycloak.

### Разграничение доступа

| Пользователь | Роль | Доступ к /reports |
|---|---|---|
| prothetic1 | prothetic_user | Да |
| prothetic2 | prothetic_user | Да |
| prothetic3 | prothetic_user | Да |
| user1 | user	 | Нет |
| user2 | user	 | Нет |
| admin1 | administrator | Нет (по усл.задачи) |


### CORS

На бэкенде через FastAPI CORS middleware:
- allow_origins = ["http://localhost:3000"]
- allow_headers = ["Authorization"]

## Запуск и тестирование

1. Склонируйте репозиторий:
```bash
git clone <repo-url>
cd <project-dir>
```

2. Запустите:
```bash
sudo docker-compose up --build
```

3. Перейдите в браузере по url:  http://localhost:3000

(Фронтенд: http://localhost:3000   
Так же доступен Keycloak Admin по адресу: http://localhost:8080 )

4. Доступ в Keycloak Admin:
```
username: admin
password: admin
```

5. Пользователи для тестирования:

|Username	| Пароль | Роль |
|---|---|---|
|prothetic1 | prothetic123 | prothetic_user |
|prothetic2 | prothetic123 | prothetic_user |
|user1 | password123 | user |

- Токен недействителен / отсутствует: ошибка 401 от API → сообщение `Not authenticated` на фронте
- Токен действителен, но нет роли: ошибка 403 от API → сообщение `Insufficient role` на фронте

## Итоги

- PKCE успешно внедрён в Keycloak и React.
- API надёжно защищён через JWT валидацию и проверку ролей.
- Генерация отчётов реализована без хранения данных, но имитирует реальные условия.
- Все требования задачи выполнены:
    - PKCE
    - Проверка токена
    - Ограничение доступа по ролям
    - Генерация индивидуальных отчётов
    
_Приложение было запущено и протестирован. В проект была добавлена директория `/testing_info` содержащая скриншоты и описание поведения работе ПО._    
см. [пример запуска ПО](testing_info/ReadMe.md)











