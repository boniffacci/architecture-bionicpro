"""Автотесты для Telemetry API."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from telemetry_api.main import TelemetryEvent, app, get_session


# Конфигурация подключения к тестовой Postgres-базе
TEST_DATABASE_URL = "postgresql://telemetry_user:telemetry_password@localhost:5445/telemetry_db"


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
    assert data["service"] == "Telemetry API"


def test_add_single_telemetry_event(client: TestClient):
    """Тест добавления одного телеметрического события."""
    event_time = datetime(2025, 3, 13, 6, 1, 9, tzinfo=timezone.utc)
    
    batch_data = {
        "events": [
            {
                "user_id": 512,
                "prosthesis_type": "arm",
                "muscle_group": "Hamstrings",
                "signal_frequency": 193,
                "signal_duration": 4250,
                "signal_amplitude": 3.89,
                "created_ts": event_time.isoformat()
            }
        ]
    }
    
    response = client.post("/telemetry", json=batch_data)
    assert response.status_code == 201
    
    data = response.json()
    assert len(data) == 1
    
    event = data[0]
    assert event["user_id"] == 512
    assert event["prosthesis_type"] == "arm"
    assert event["muscle_group"] == "Hamstrings"
    assert event["signal_frequency"] == 193
    assert event["signal_duration"] == 4250
    assert event["signal_amplitude"] == 3.89
    assert "id" in event
    assert "saved_ts" in event


def test_add_multiple_telemetry_events(client: TestClient):
    """Тест добавления нескольких телеметрических событий."""
    batch_data = {
        "events": [
            {
                "user_id": 887,
                "prosthesis_type": "arm",
                "muscle_group": "Biceps",
                "signal_frequency": 489,
                "signal_duration": 3702,
                "signal_amplitude": 4.46,
                "created_ts": "2025-03-04T23:12:31Z"
            },
            {
                "user_id": 866,
                "prosthesis_type": "hand",
                "muscle_group": "Biceps",
                "signal_frequency": 102,
                "signal_duration": 3630,
                "signal_amplitude": 4.49,
                "created_ts": "2025-02-26T19:39:02Z"
            },
            {
                "user_id": 961,
                "prosthesis_type": "arm",
                "muscle_group": "Gastrocnemius",
                "signal_frequency": 348,
                "signal_duration": 1146,
                "signal_amplitude": 2.87,
                "created_ts": "2025-03-25T02:30:36Z"
            }
        ]
    }
    
    response = client.post("/telemetry", json=batch_data)
    assert response.status_code == 201
    
    data = response.json()
    assert len(data) == 3
    
    # Проверяем, что все события сохранены
    assert data[0]["user_id"] == 887
    assert data[1]["user_id"] == 866
    assert data[2]["user_id"] == 961
    
    # Проверяем, что у всех событий есть ID и saved_ts
    for event in data:
        assert "id" in event
        assert "saved_ts" in event


def test_add_empty_events_list(client: TestClient):
    """Тест попытки добавления пустого списка событий."""
    batch_data = {"events": []}
    
    response = client.post("/telemetry", json=batch_data)
    assert response.status_code == 400
    assert "не может быть пустым" in response.json()["detail"]


def test_add_events_with_different_prosthesis_types(client: TestClient):
    """Тест добавления событий с разными типами протезов."""
    batch_data = {
        "events": [
            {
                "user_id": 100,
                "prosthesis_type": "arm",
                "muscle_group": "Biceps",
                "signal_frequency": 200,
                "signal_duration": 1000,
                "signal_amplitude": 3.5,
                "created_ts": "2025-01-01T12:00:00Z"
            },
            {
                "user_id": 101,
                "prosthesis_type": "hand",
                "muscle_group": "Triceps",
                "signal_frequency": 250,
                "signal_duration": 1500,
                "signal_amplitude": 4.0,
                "created_ts": "2025-01-01T12:05:00Z"
            },
            {
                "user_id": 102,
                "prosthesis_type": "leg",
                "muscle_group": "Quadriceps",
                "signal_frequency": 300,
                "signal_duration": 2000,
                "signal_amplitude": 5.5,
                "created_ts": "2025-01-01T12:10:00Z"
            }
        ]
    }
    
    response = client.post("/telemetry", json=batch_data)
    assert response.status_code == 201
    
    data = response.json()
    assert len(data) == 3
    assert data[0]["prosthesis_type"] == "arm"
    assert data[1]["prosthesis_type"] == "hand"
    assert data[2]["prosthesis_type"] == "leg"


def test_saved_ts_is_set_automatically(client: TestClient):
    """Тест автоматической установки saved_ts."""
    batch_data = {
        "events": [
            {
                "user_id": 999,
                "prosthesis_type": "arm",
                "muscle_group": "Deltoid",
                "signal_frequency": 150,
                "signal_duration": 800,
                "signal_amplitude": 2.5,
                "created_ts": "2025-01-01T10:00:00Z"
            }
        ]
    }
    
    response = client.post("/telemetry", json=batch_data)
    assert response.status_code == 201
    
    data = response.json()
    event = data[0]
    
    # Проверяем, что saved_ts установлен и отличается от created_ts
    assert event["saved_ts"] is not None
    # saved_ts должен быть позже, чем created_ts (событие из прошлого)
    saved_ts = datetime.fromisoformat(event["saved_ts"].replace("Z", "+00:00"))
    created_ts_value = datetime.fromisoformat(event["created_ts"].replace("Z", "+00:00"))
    assert saved_ts > created_ts_value


def test_missing_required_fields(client: TestClient):
    """Тест попытки добавления события без обязательных полей."""
    # Попытка добавления без user_id
    batch_data = {
        "events": [
            {
                "prosthesis_type": "arm",
                "muscle_group": "Biceps",
                "signal_frequency": 200,
                "signal_duration": 1000,
                "signal_amplitude": 3.5,
                "created_ts": "2025-01-01T12:00:00Z"
            }
        ]
    }
    
    response = client.post("/telemetry", json=batch_data)
    assert response.status_code == 422


def test_large_batch_of_events(client: TestClient):
    """Тест добавления большого пакета событий."""
    events = []
    for i in range(100):
        events.append({
            "user_id": i,
            "prosthesis_type": "arm" if i % 2 == 0 else "hand",
            "muscle_group": "Biceps",
            "signal_frequency": 100 + i,
            "signal_duration": 1000 + i * 10,
            "signal_amplitude": 2.0 + i * 0.01,
            "created_ts": f"2025-01-01T{i % 24:02d}:00:00Z"
        })
    
    batch_data = {"events": events}
    
    response = client.post("/telemetry", json=batch_data)
    assert response.status_code == 201
    
    data = response.json()
    assert len(data) == 100
    
    # Проверяем, что все события имеют уникальные ID
    ids = [event["id"] for event in data]
    assert len(ids) == len(set(ids))


def test_populate_base(client: TestClient):
    """Тест эндпоинта /populate_base для пересоздания и наполнения БД."""
    from telemetry_api.main import TelemetryEvent, engine
    from sqlmodel import Session, select
    
    # Вызываем эндпоинт populate_base
    response = client.post("/populate_base")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "events_loaded" in data
    assert data["events_loaded"] == 10000  # Точное количество строк в CSV
    
    # Создаем новую сессию для проверки данных (после пересоздания схемы)
    with Session(engine) as new_session:
        statement = select(TelemetryEvent)
        events = new_session.exec(statement).all()
        
        # Должно быть загружено ровно 10000 событий
        assert len(events) == 10000
        assert len(events) == data["events_loaded"]
        
        # Проверяем, что у первого события есть все необходимые поля
        if events:
            first_event = events[0]
            assert first_event.id is not None
            assert first_event.event_uuid is not None
            assert first_event.user_id is not None
            assert first_event.prosthesis_type is not None
            assert first_event.muscle_group is not None
            assert first_event.signal_frequency is not None
            assert first_event.created_ts is not None


def test_populate_base_recreates_schema(client: TestClient):
    """Тест что /populate_base пересоздает схему БД."""
    from telemetry_api.main import TelemetryEvent, engine
    from sqlmodel import Session as SQLSession, select
    
    # Создаем сессию и добавляем тестовое событие
    with SQLSession(engine) as session:
        test_event = TelemetryEvent(
            event_uuid="test-uuid-99999",
            user_id=99999,
            prosthesis_type="test",
            muscle_group="TestMuscle",
            signal_frequency=100,
            signal_duration=1000,
            signal_amplitude=1.0,
            created_ts=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        session.add(test_event)
        session.commit()
        
        # Проверяем, что событие добавлено
        statement = select(TelemetryEvent).where(TelemetryEvent.user_id == 99999)
        event_before = session.exec(statement).first()
        assert event_before is not None
    
    # Вызываем populate_base
    response = client.post("/populate_base")
    assert response.status_code == 200
    
    # Создаем новую сессию для проверки (после пересоздания схемы)
    with SQLSession(engine) as new_session:
        statement = select(TelemetryEvent).where(TelemetryEvent.user_id == 99999)
        event_after = new_session.exec(statement).first()
        # Старое событие должно быть удалено (схема пересоздана)
        assert event_after is None
        
        # Проверяем, что загружены данные из CSV (ровно 10000 записей)
        all_events = new_session.exec(select(TelemetryEvent)).all()
        assert len(all_events) == 10000
