"""Configuration for auth_proxy service."""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки auth_proxy сервиса."""
    
    # Redis settings
    redis_host: str = "localhost"  # Хост Redis сервера
    redis_port: int = 6379  # Порт Redis сервера
    redis_db: int = 0  # Номер базы данных Redis
    redis_password: Optional[str] = None  # Пароль для Redis (если требуется)
    
    # Keycloak OIDC settings
    keycloak_url: str = "http://localhost:8080"  # URL Keycloak сервера
    keycloak_realm: str = "reports-realm"  # Имя realm в Keycloak
    client_id: str = "auth-proxy"  # Client ID для OIDC
    client_secret: Optional[str] = "auth-proxy-secret-key-12345"  # Client secret (для confidential clients)
    
    # Session settings
    session_cookie_name: str = "session_id"  # Имя cookie для session ID
    session_lifetime_seconds: int = 3600  # Время жизни сессии (по умолчанию 1 час)
    session_cookie_secure: bool = False  # Использовать Secure flag для cookie (True для HTTPS)
    session_cookie_samesite: str = "lax"  # SameSite policy: strict, lax, none
    session_cookie_httponly: bool = True  # HttpOnly flag для cookie
    session_cookie_path: str = "/"  # Path для cookie
    
    # Session rotation settings
    enable_session_rotation: bool = True  # Включить ротацию session ID при каждом запросе
    
    # Single session per user settings
    single_session_per_user: bool = True  # Разрешить только одну активную сессию на пользователя
    single_session_for_roles: list[str] = ["administrators"]  # Роли, для которых действует ограничение (если не для всех)
    
    # Auth proxy settings
    auth_proxy_host: str = "0.0.0.0"  # Хост для запуска auth_proxy
    auth_proxy_port: int = 3002  # Порт для запуска auth_proxy
    
    # Frontend redirect URL
    frontend_url: str = "http://localhost:5173"  # URL фронтенда для редиректов после авторизации
    
    class Config:
        env_file = ".env"  # Загружать настройки из .env файла
        env_prefix = "AUTH_PROXY_"  # Префикс для переменных окружения


# Создаем глобальный экземпляр настроек
settings = Settings()
