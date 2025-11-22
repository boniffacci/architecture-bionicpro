"""Основной модуль Telemetry API для сбора телеметрии с бионических протезов."""

import asyncio
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine

# Настраиваем базовый уровень логирования на INFO
logging.basicConfig(level=logging.INFO)

# Создаем экземпляр FastAPI для определения маршрутов сервиса
app = FastAPI(title="Telemetry API", description="API для сбора телеметрии с бионических протезов")

# Добавляем промежуточное ПО для поддержки CORS-запросов
app.add_middleware(
    CORSMiddleware,  # Класс промежуточного ПО для CORS
    allow_origins=["*"],  # Разрешаем запросы со всех доменов
    allow_credentials=True,  # Разрешаем передачу cookies и авторизационных заголовков
    allow_methods=["*"],  # Разрешаем все HTTP-методы
    allow_headers=["*"],  # Разрешаем любые заголовки в запросах
)


# Настройки подключения к базе данных
class DatabaseConfig:
    """Конфигурация подключения к PostgreSQL базе данных телеметрии."""

    host: str = "localhost"  # Хост базы данных
    port: int = 5445  # Порт базы данных (из docker-compose.yaml)
    database: str = "telemetry_db"  # Имя базы данных
    user: str = "telemetry_user"  # Пользователь БД
    password: str = "telemetry_password"  # Пароль пользователя

    @classmethod
    def get_connection_string(cls) -> str:
        """Формирует строку подключения к PostgreSQL."""
        return f"postgresql://{cls.user}:{cls.password}@{cls.host}:{cls.port}/{cls.database}"


# Модель телеметрического события для базы данных
class EmgSensorData(SQLModel, table=True):
    """
    Модель данных EMG-сенсора бионического протеза.
    Используется как для таблицы БД, так и для Pydantic-валидации.
    """

    __tablename__ = "emg_sensor_data"  # Имя таблицы в БД

    id: Optional[int] = Field(default=None, primary_key=True, description="Уникальный идентификатор записи")
    user_id: int = Field(description="Идентификатор пользователя протеза")
    prosthesis_type: str = Field(max_length=50, description="Тип протеза (arm, hand, leg и т.д.)")
    muscle_group: str = Field(max_length=100, description="Группа мышц (Biceps, Hamstrings, Gastrocnemius и т.д.)")
    signal_frequency: int = Field(description="Частота сигнала в Гц")
    signal_duration: int = Field(description="Длительность сигнала в миллисекундах")
    signal_amplitude: float = Field(description="Амплитуда сигнала")
    signal_time: datetime = Field(description="Время снятия сигнала на стороне протеза (created_ts)")
    saved_ts: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Время сохранения события в БД на стороне сервера (UTC)",
    )


# Модель для входных данных при создании события
class EmgSensorDataCreate(SQLModel):
    """Модель для создания нового телеметрического события (входные данные API)."""

    user_id: int = Field(description="Идентификатор пользователя протеза")
    prosthesis_type: str = Field(max_length=50, description="Тип протеза (arm, hand, leg и т.д.)")
    muscle_group: str = Field(max_length=100, description="Группа мышц (Biceps, Hamstrings, Gastrocnemius и т.д.)")
    signal_frequency: int = Field(description="Частота сигнала в Гц")
    signal_duration: int = Field(description="Длительность сигнала в миллисекундах")
    signal_amplitude: float = Field(description="Амплитуда сигнала")
    created_ts: datetime = Field(description="Время создания события на стороне протеза")


# Модель для списка событий
class EmgSensorDataBatch(SQLModel):
    """Модель для пакетной загрузки телеметрических событий."""

    events: List[EmgSensorDataCreate] = Field(description="Список телеметрических событий для сохранения")


# Создаем движок базы данных
engine = create_engine(DatabaseConfig.get_connection_string(), echo=True)  # Логируем все SQL-запросы


def create_db_and_tables():
    """Создает таблицы в базе данных, если они не существуют."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency для получения сессии базы данных."""
    with Session(engine) as session:
        yield session


@app.on_event("startup")
def on_startup():
    """Обработчик события запуска приложения."""
    logging.info("Запуск Telemetry API...")
    create_db_and_tables()
    logging.info("Таблицы БД созданы/проверены")


@app.post("/telemetry", response_model=List[EmgSensorData], status_code=201)
async def add_telemetry_events(
    batch: EmgSensorDataBatch, session: Session = Depends(get_session)
) -> List[EmgSensorData]:
    """
    Добавление списка телеметрических событий в БД.

    Args:
        batch: Пакет телеметрических событий
        session: Сессия базы данных

    Returns:
        List[EmgSensorData]: Список сохраненных событий с присвоенными ID и saved_ts
    """
    if not batch.events:
        raise HTTPException(status_code=400, detail="Список событий не может быть пустым")

    saved_events = []
    current_time = datetime.now(timezone.utc)

    for event_data in batch.events:
        # Создаем новое событие
        new_event = EmgSensorData(
            user_id=event_data.user_id,
            prosthesis_type=event_data.prosthesis_type,
            muscle_group=event_data.muscle_group,
            signal_frequency=event_data.signal_frequency,
            signal_duration=event_data.signal_duration,
            signal_amplitude=event_data.signal_amplitude,
            signal_time=event_data.created_ts,
            saved_ts=current_time,
        )

        session.add(new_event)
        saved_events.append(new_event)

    # Сохраняем все события одной транзакцией
    session.commit()

    # Обновляем объекты, чтобы получить присвоенные ID
    for event in saved_events:
        session.refresh(event)

    logging.info(f"Сохранено {len(saved_events)} телеметрических событий")

    return saved_events


@app.get("/health")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "healthy", "service": "Telemetry API"}


@app.post("/populate_base")
async def populate_base(session: Session = Depends(get_session)):
    """
    Пересоздает схему БД и наполняет её тестовыми данными из signal_samples.csv.
    
    Args:
        session: Сессия базы данных
        
    Returns:
        dict: Статистика загрузки данных
    """
    # Путь к CSV-файлу
    csv_path = Path(__file__).parent / "signal_samples.csv"
    
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"CSV-файл не найден: {csv_path}")
    
    # Пересоздаем схему БД (удаляем и создаем заново все таблицы)
    logging.info("Пересоздание схемы БД...")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    logging.info("Схема БД пересоздана")
    
    # Читаем и загружаем данные из CSV
    events_loaded = 0
    
    # Используем asyncio для асинхронной обработки
    await asyncio.sleep(0)  # Уступаем управление event loop
    
    with open(csv_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            # Парсим дату из CSV (формат: "2025-03-13 06:01:09")
            signal_time = datetime.strptime(row["signal_time"], "%Y-%m-%d %H:%M:%S")
            # Добавляем timezone UTC
            signal_time = signal_time.replace(tzinfo=timezone.utc)
            
            # Создаем событие из строки CSV
            event = EmgSensorData(
                user_id=int(row["user_id"]),
                prosthesis_type=row["prosthesis_type"],
                muscle_group=row["muscle_group"],
                signal_frequency=int(row["signal_frequency"]),
                signal_duration=int(row["signal_duration"]),
                signal_amplitude=float(row["signal_amplitude"]),
                signal_time=signal_time,
                saved_ts=datetime.now(timezone.utc),
            )
            
            session.add(event)
            events_loaded += 1
            
            # Периодически уступаем управление event loop
            if events_loaded % 100 == 0:
                await asyncio.sleep(0)
    
    # Сохраняем все изменения
    session.commit()
    
    logging.info(f"Загружено {events_loaded} телеметрических событий из CSV")
    
    return {
        "status": "success",
        "message": "База данных пересоздана и наполнена тестовыми данными",
        "events_loaded": events_loaded,
    }


# Запускаем приложение, если файл выполняется напрямую
if __name__ == "__main__":
    import asyncio
    from uvicorn import Config, Server

    # Создаем конфигурацию сервера
    config = Config(app, host="0.0.0.0", port=3003)
    # Создаем экземпляр сервера
    server = Server(config)
    # Запускаем сервер с asyncio.run
    asyncio.run(server.serve())
