"""Автотесты для CRM API."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from crm_api.main import Customer, app, get_session


# Фикстура для создания тестовой БД в памяти
@pytest.fixture(name="session")
def session_fixture():
    """Создает тестовую сессию БД в памяти."""
    # Создаем движок SQLite в памяти для тестов
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Создаем все таблицы
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


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


def test_register_customer_gerard_kikoine(client: TestClient):
    """Тест регистрации Жерара Кикоина."""
    customer_data = {
        "name": "Gérard Kikoïne",
        "email": "gerard.kikoine@example.fr",
        "age": 75,
        "gender": "Male",
        "country": "France",
        "address": "123 Rue de la Pornographie, Paris",
        "phone": "+33-1-23-45-67-89",
    }

    response = client.post("/register", json=customer_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == customer_data["name"]
    assert data["email"] == customer_data["email"]
    assert data["age"] == customer_data["age"]
    assert data["gender"] == customer_data["gender"]
    assert data["country"] == customer_data["country"]
    assert data["address"] == customer_data["address"]
    assert data["phone"] == customer_data["phone"]
    assert "id" in data
    assert "registered_at" in data


def test_register_customer_brigitte_lahaie(client: TestClient):
    """Тест регистрации несравненной Бриджит Ляэ."""
    customer_data = {
        "name": "Brigitte Lahaie",
        "email": "brigitte.lahaie@example.fr",
        "age": 69,
        "gender": "Female",
        "country": "France",
        "address": "456 Avenue des Stars, Paris",
        "phone": "+33-1-98-76-54-32",
    }

    response = client.post("/register", json=customer_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == customer_data["name"]
    assert data["email"] == customer_data["email"]
    assert data["age"] == customer_data["age"]


def test_register_customer_sylvia_bourdon(client: TestClient):
    """Тест регистрации Сильвии Бурдон."""
    customer_data = {
        "name": "Sylvia Bourdon",
        "email": "sylvia.bourdon@example.fr",
        "age": 70,
        "gender": "Female",
        "country": "France",
        "address": "789 Boulevard du Cinéma, Lyon",
        "phone": "+33-4-11-22-33-44",
    }

    response = client.post("/register", json=customer_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == customer_data["name"]
    assert data["email"] == customer_data["email"]


def test_register_customer_alban_ceray(client: TestClient):
    """Тест регистрации Альбана Сере."""
    customer_data = {
        "name": "Alban Ceray",
        "email": "alban.ceray@example.fr",
        "age": 76,
        "gender": "Male",
        "country": "France",
        "address": "321 Rue du Film, Marseille",
        "phone": "+33-4-55-66-77-88",
    }

    response = client.post("/register", json=customer_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == customer_data["name"]
    assert data["email"] == customer_data["email"]


def test_register_customer_duplicate_email(client: TestClient):
    """Тест попытки регистрации с дублирующимся email."""
    customer_data = {
        "name": "Richard Lemieuvre",
        "email": "richard.lemieuvre@example.fr",
        "age": 74,
        "gender": "Male",
        "country": "France",
        "address": "555 Rue de l'Acteur, Nice",
        "phone": "+33-4-99-88-77-66",
    }

    # Первая регистрация должна пройти успешно
    response1 = client.post("/register", json=customer_data)
    assert response1.status_code == 201

    # Вторая регистрация с тем же email должна вернуть ошибку
    response2 = client.post("/register", json=customer_data)
    assert response2.status_code == 400
    assert "уже зарегистрирован" in response2.json()["detail"]


def test_register_customer_minimal_data(client: TestClient):
    """Тест регистрации с минимальным набором данных."""
    customer_data = {"name": "Marilyn Jess", "email": "marilyn.jess@example.fr"}

    response = client.post("/register", json=customer_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == customer_data["name"]
    assert data["email"] == customer_data["email"]
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
