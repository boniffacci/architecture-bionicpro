"""Основной модуль CRM API для регистрации пользователей интернет-магазина."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select

# Настраиваем базовый уровень логирования на INFO
logging.basicConfig(level=logging.INFO)

# Создаем экземпляр FastAPI для определения маршрутов сервиса
app = FastAPI(title="CRM API", description="API для регистрации пользователей интернет-магазина")

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
    """Конфигурация подключения к PostgreSQL базе данных CRM."""

    host: str = "localhost"  # Хост базы данных
    port: int = 5444  # Порт базы данных (из docker-compose.yaml)
    database: str = "crm_db"  # Имя базы данных
    user: str = "crm_user"  # Пользователь БД
    password: str = "crm_password"  # Пароль пользователя

    @classmethod
    def get_connection_string(cls) -> str:
        """Формирует строку подключения к PostgreSQL."""
        return f"postgresql://{cls.user}:{cls.password}@{cls.host}:{cls.port}/{cls.database}"


# Модель клиента (Customer) для базы данных и API
class Customer(SQLModel, table=True):
    """
    Модель клиента интернет-магазина.
    Используется как для таблицы БД, так и для Pydantic-валидации.
    """

    __tablename__ = "customers"  # Имя таблицы в БД

    id: Optional[int] = Field(default=None, primary_key=True, description="Уникальный идентификатор клиента")
    name: str = Field(max_length=100, description="Полное имя клиента")
    email: str = Field(max_length=100, unique=True, index=True, description="Email клиента (уникальный)")
    age: Optional[int] = Field(default=None, description="Возраст клиента")
    gender: Optional[str] = Field(default=None, max_length=10, description="Пол клиента")
    country: Optional[str] = Field(default=None, max_length=100, description="Страна проживания")
    address: Optional[str] = Field(default=None, max_length=255, description="Адрес клиента")
    phone: Optional[str] = Field(default=None, max_length=25, description="Номер телефона")
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Дата и время регистрации (UTC)"
    )


# Модель для входных данных при регистрации (без id и registered_at)
class CustomerCreate(SQLModel):
    """Модель для создания нового клиента (входные данные API)."""

    name: str = Field(max_length=100, description="Полное имя клиента")
    email: str = Field(max_length=100, description="Email клиента (должен быть уникальным)")
    age: Optional[int] = Field(default=None, description="Возраст клиента")
    gender: Optional[str] = Field(default=None, max_length=10, description="Пол клиента")
    country: Optional[str] = Field(default=None, max_length=100, description="Страна проживания")
    address: Optional[str] = Field(default=None, max_length=255, description="Адрес клиента")
    phone: Optional[str] = Field(default=None, max_length=25, description="Номер телефона")


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
    logging.info("Запуск CRM API...")
    create_db_and_tables()
    logging.info("Таблицы БД созданы/проверены")


@app.post("/register", response_model=Customer, status_code=201)
async def register_customer(customer_data: CustomerCreate, session: Session = Depends(get_session)) -> Customer:
    """
    Регистрация нового клиента в системе.

    Args:
        customer_data: Данные нового клиента
        session: Сессия базы данных

    Returns:
        Customer: Созданный клиент с присвоенным ID и временем регистрации

    Raises:
        HTTPException: 400 если email уже существует в системе
    """
    # Проверяем, существует ли клиент с таким email
    statement = select(Customer).where(Customer.email == customer_data.email)
    existing_customer = session.exec(statement).first()

    if existing_customer:
        logging.warning(f"Попытка регистрации с существующим email: {customer_data.email}")
        raise HTTPException(status_code=400, detail=f"Клиент с email {customer_data.email} уже зарегистрирован")

    # Создаем нового клиента
    new_customer = Customer(
        name=customer_data.name,
        email=customer_data.email,
        age=customer_data.age,
        gender=customer_data.gender,
        country=customer_data.country,
        address=customer_data.address,
        phone=customer_data.phone,
        registered_at=datetime.now(timezone.utc),
    )

    # Сохраняем в БД
    session.add(new_customer)
    session.commit()
    session.refresh(new_customer)

    logging.info(f"Зарегистрирован новый клиент: {new_customer.email} (ID: {new_customer.id})")

    return new_customer


@app.get("/health")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "healthy", "service": "CRM API"}


# Запускаем приложение, если файл выполняется напрямую
if __name__ == "__main__":
    import asyncio
    from uvicorn import Config, Server

    # Создаем конфигурацию сервера
    config = Config(app, host="0.0.0.0", port=3002)
    # Создаем экземпляр сервера
    server = Server(config)
    # Запускаем сервер с asyncio.run
    asyncio.run(server.serve())
