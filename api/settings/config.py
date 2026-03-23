"""
Centralized environment variable declaration & type conversion.
os.environ must not appear in other files!
"""
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class ENV(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Django
    DEBUG: bool = True
    ALLOWED_HOSTS: List[str] = ["*"]

    # PostgreSQL
    DB_NAME: str = "review"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_QUEUE: str = "file_parsing"

    # RabbitMQ
    MQ_HOST: str = "rabbitmq"
    MQ_PORT: int = 5672
    MQ_USERNAME: str = "guest"
    MQ_PASSWORD: str = "guest"
    MQ_VIRTUAL_HOST: str = "/"
    MQ_QUEUE_NAME: str = "task_master"
    MQ_QUEUE_NAME_LLM_TEST: str = "llm_test"

    # Email
    EMAIL_HOST: str = "smtp.qq.com"
    EMAIL_PORT: int = 465
    EMAIL_USE_SSL: bool = True
    EMAIL_HOST_USER: str = ""
    EMAIL_HOST_PASSWORD: str = ""
    VERIFICATION_CODE_EXPIRE: int = 300

    # File upload
    SUPER_USER_LIST: List[str] = []
    MAX_UPLOAD_FILES: int = 5
    MAX_FILE_SIZE: int = 10
    DOMAIN_NAME: str = "http://vectasurge.com"

    # Default LLM configuration
    DEFAULT_MODEL_NAME: str = "qwen3-32b"
    DEFAULT_MODEL_URL: str = "qwen3-32b"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_FREQUENCY_PENALTY: float = 0.0
    DEFAULT_TOP_P: float = 1.0
    DEFAULT_CHUNK_LENGTH: int = 8192

    @field_validator("ALLOWED_HOSTS", "SUPER_USER_LIST", mode="before")
    @classmethod
    def split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


env = ENV()
