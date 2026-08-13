from os import getenv

import pytz
from dotenv import load_dotenv

load_dotenv()


class BaseSettings:
    def __init__(self):
        for name, annotation in self.__annotations__.items():
            env_value = getenv(name)
            default_value = getattr(self.__class__, name, None)

            if env_value is None:
                setattr(self, name, default_value)
            else:
                setattr(self, name, annotation(env_value))


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"

    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_URL: str = "http://127.0.0.1:9000"

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    JWT_TOKEN_LIFETIME: int = 12
    JWT_SECRET_KEY: str = "my-secret-key"

    TIMEZONE: pytz.timezone = "Europe/Moscow"

    ENGINE: str = "sqlite+aiosqlite:///./local.db"


settings = Settings()
