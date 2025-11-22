"""Автотесты для CRM API."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from crm_api.main import User, app, get_session


# Конфигурация подключения к тестовой Postgres-базе
TEST_DATABASE_URL = "postgresql://crm_user:crm_password@localhost:5444/crm_db"


# Фикстура для создания тестовой БД с полной очисткой
@pytest.fixture(name="session", scope="function")
def session_fixture():
    """Создает тестовую сессию БД с подключением к Postgres и полной очисткой схемы."""
    # Создаем движок для подключения к Postgres
    engine = create_engine(TEST_DATABASE_URL, echo=True)
    
    # Полностью удаляем все таблицы (пересоздание схемы)
    SQLModel.metadata.drop_all(engine)
    
    # Создаем все таблицы заново
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session
    
    # После теста снова очищаем
    SQLModel.metadata.drop_all(engine)


# Фикстура для тестового клиента FastAPI
@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Создает тестовый клиент FastAPI с тестовой БД."""

    def get_session_override():
        return session

    # Переопределяем зависимость get_session
    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client

    # Очищаем переопределения после теста
    app.dependency_overrides.clear()


def test_health_check(client: TestClient):
    """Тест проверки работоспособности API."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "CRM API"


def test_register_user_gerard_kikoine(client: TestClient):
    """Тест регистрации Жерара Кикоина."""
    user_data = {
        "name": "Gérard Kikoïne",
        "email": "gerard.kikoine@example.fr",
        "age": 75,
        "gender": "Male",
        "country": "France",
        "address": "123 Rue de la Pornographie, Paris",
        "phone": "+33-1-23-45-67-89",
    }

    response = client.post("/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]
    assert data["age"] == user_data["age"]
    assert data["gender"] == user_data["gender"]
    assert data["country"] == user_data["country"]
    assert data["address"] == user_data["address"]
    assert data["phone"] == user_data["phone"]
    assert "id" in data
    assert "registered_at" in data


def test_register_customer_brigitte_lahaie(client: TestClient):
    """Тест регистрации несравненной Бриджит Ляэ."""
    user_data = {
        "name": "Brigitte Lahaie",
        "email": "brigitte.lahaie@example.fr",
        "age": 69,
        "gender": "Female",
        "country": "France",
        "address": "456 Avenue des Stars, Paris",
        "phone": "+33-1-98-76-54-32",
    }

    response = client.post("/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]
    assert data["age"] == user_data["age"]


def test_register_customer_sylvia_bourdon(client: TestClient):
    """Тест регистрации Сильвии Бурдон."""
    user_data = {
        "name": "Sylvia Bourdon",
        "email": "sylvia.bourdon@example.fr",
        "age": 70,
        "gender": "Female",
        "country": "France",
        "address": "789 Boulevard du Cinéma, Lyon",
        "phone": "+33-4-11-22-33-44",
    }

    response = client.post("/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]


def test_register_customer_alban_ceray(client: TestClient):
    """Тест регистрации Альбана Сере."""
    user_data = {
        "name": "Alban Ceray",
        "email": "alban.ceray@example.fr",
        "age": 76,
        "gender": "Male",
        "country": "France",
        "address": "321 Rue du Film, Marseille",
        "phone": "+33-4-55-66-77-88",
    }

    response = client.post("/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]


def test_register_customer_duplicate_email(client: TestClient):
    """Тест попытки регистрации с дублирующимся email."""
    user_data = {
        "name": "Richard Lemieuvre",
        "email": "richard.lemieuvre@example.fr",
        "age": 74,
        "gender": "Male",
        "country": "France",
        "address": "555 Rue de l'Acteur, Nice",
        "phone": "+33-4-99-88-77-66",
    }

    # Первая регистрация должна пройти успешно
    response1 = client.post("/register", json=user_data)
    assert response1.status_code == 201

    # Вторая регистрация с тем же email должна вернуть ошибку
    response2 = client.post("/register", json=user_data)
    assert response2.status_code == 400
    assert "уже зарегистрирован" in response2.json()["detail"]


def test_register_customer_minimal_data(client: TestClient):
    """Тест регистрации с минимальным набором данных."""
    user_data = {"name": "Marilyn Jess", "email": "marilyn.jess@example.fr"}

    response = client.post("/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]
    assert data["age"] is None
    assert data["gender"] is None
    assert data["country"] is None
    assert data["address"] is None
    assert data["phone"] is None


def test_register_customer_missing_required_fields(client: TestClient):
    """Тест регистрации без обязательных полей."""
    # Попытка регистрации без имени
    response1 = client.post("/register", json={"email": "test@example.fr"})
    assert response1.status_code == 422

    # Попытка регистрации без email
    response2 = client.post("/register", json={"name": "Test User"})
    assert response2.status_code == 422

    # Попытка регистрации без данных вообще
    response3 = client.post("/register", json={})
    assert response3.status_code == 422


def test_populate_base(client: TestClient):
    """Тест эндпоинта /populate_base для пересоздания и наполнения БД."""
    from crm_api.main import User, engine
    from sqlmodel import Session, select
    
    # Вызываем эндпоинт populate_base
    response = client.post("/populate_base")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "users_loaded" in data
    assert data["users_loaded"] == 1000  # Точное количество строк в CSV
    
    # Создаем новую сессию для проверки данных (после пересоздания схемы)
    with Session(engine) as new_session:
        statement = select(User)
        users = new_session.exec(statement).all()
        
        # Должно быть загружено ровно 1000 пользователей
        assert len(users) == 1000
        assert len(users) == data["users_loaded"]
        
        # Проверяем, что у первого пользователя есть все необходимые поля
        if users:
            first_user = users[0]
            assert first_user.id is not None
            assert first_user.user_uuid is not None
            assert first_user.name is not None
            assert first_user.email is not None
            assert first_user.registered_at is not None


def test_populate_base_recreates_schema(client: TestClient):
    """Тест что /populate_base пересоздает схему БД."""
    from datetime import datetime, timezone
    from crm_api.main import User, engine
    from sqlmodel import Session as SQLSession, select
    
    # Создаем сессию и добавляем тестового пользователя
    with SQLSession(engine) as session:
        test_user = User(
            user_uuid="test-uuid-12345",
            name="Test User Before Populate",
            email="test.before@example.com",
            registered_at=datetime.now(timezone.utc),
        )
        session.add(test_user)
        session.commit()
        
        # Проверяем, что пользователь добавлен
        statement = select(User).where(User.email == "test.before@example.com")
        user_before = session.exec(statement).first()
        assert user_before is not None
    
    # Вызываем populate_base
    response = client.post("/populate_base")
    assert response.status_code == 200
    
    # Создаем новую сессию для проверки (после пересоздания схемы)
    with SQLSession(engine) as new_session:
        statement = select(User).where(User.email == "test.before@example.com")
        user_after = new_session.exec(statement).first()
        # Старый пользователь должен быть удален (схема пересоздана)
        assert user_after is None
        
        # Проверяем, что загружены данные из CSV (ровно 1000 записей)
        all_users = new_session.exec(select(User)).all()
        assert len(all_users) == 1000
