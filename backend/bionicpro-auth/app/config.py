from pydantic_settings import BaseSettings
from typing import Optional

class Config(BaseSettings):
    # Keycloak
    keycloak_url: str = "http://keycloak:8080"
    keycloak_client_id: str = "backend-auth"
    keycloak_secret: str = "Y2MCU5BjY8tzCajrWtFLKTINH7kffiHG"
    keycloak_realm: str = "reports-realm"
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # App
    app_port: int = 5001
    app_debug: bool = False
    
    class Config:
        env_file = ".env"

config = Config()