"""
Centralized declaration & type conversion, os.environ must not appear in other files!
"""
import dotenv
from decouple import config, Csv
from pathlib import Path
from api.common.utils.logger import logger

# BASE_DIR should be the project root directory, which is the directory where env.py is located
BASE_DIR = Path(__file__).resolve().parent
try:
    dotenv.load_dotenv(BASE_DIR / ".env")
    logger.info(f"Loaded .env file from: {BASE_DIR / '.env'}")
except Exception as e:
    logger.info("Using system environment variables and default values")


class ENV:
    # Required items (no default value, ImproperlyConfigured will be raised if missing)
    DEBUG = config("DEBUG", default=True, cast=bool)
    # ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*", cast=Csv())
    # mysql configuration
    DB_NAME = config("DB_NAME", default="review")
    DB_USER = config("DB_USER", default="root")
    DB_PASSWORD = config("DB_PASSWORD", default="root")
    DB_HOST = config("DB_HOST", default="localhost")
    DB_PORT = config("DB_PORT", default="3306")

    # redis configuration
    REDIS_HOST = config("REDIS_HOST", default="redis")
    REDIS_PORT = config("REDIS_PORT", default="6379", cast=int)
    REDIS_DB = config("REDIS_DB", default="0", cast=int)
    REDIS_QUEUE = config("REDIS_QUEUE", default="file_parsing")

    # rabbitmq configuration
    MQ_HOST = config("MQ_HOST", default="rabbitmq")
    MQ_PORT = config("MQ_PORT", default="5672", cast=int)
    MQ_USERNAME = config("MQ_USERNAME", default="guest")
    MQ_PASSWORD = config("MQ_PASSWORD", default="guest")
    MQ_VIRTUAL_HOST = config("MQ_VIRTUAL_HOST", default="/")
    MQ_QUEUE_NAME = config("MQ_QUEUE_NAME", default="task_master")
    MQ_QUEUE_NAME_LLM_TEST = config("MQ_QUEUE_NAME_LLM_TEST", default="llm_test")
    # Email configuration
    EMAIL_HOST = config("EMAIL_HOST", default="smtp.qq.com")  # Or your email service provider
    EMAIL_PORT = config("EMAIL_PORT", default="465", cast=int)
    EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=True, cast=bool)
    EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="2386677465@qq.com")  # Your email
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="gdmaomlmoxohdjci")  # Email authorization code, not password
    VERIFICATION_CODE_EXPIRE = config("VERIFICATION_CODE_EXPIRE", default="300", cast=int)  # Verification code expiration time

    # File upload configuration
    SUPER_USER_LIST = config("SUPER_USER_LIST", default="shuhaojie,wangchangming,wanglepeng,wangpeng", cast=Csv())
    MAX_UPLOAD_FILES = config("MAX_UPLOAD_FILES", default=5, cast=int)
    MAX_FILE_SIZE = config("MAX_FILE_SIZE", default=10, cast=int)
    DOMAIN_NAME = config("DOMAIN_NAME", default="http://vectasurge.com")

    # Default large model configuration, used by initialization script
    DEFAULT_MODEL_NAME = config("DEFAULT_MODEL_NAME", default="qwen3-32b")
    DEFAULT_MODEL_URL = config("DEFAULT_MODEL_URL", default="qwen3-32b")
    DEFAULT_TEMPERATURE = config("DEFAULT_TEMPERATURE", default="0.7", cast=float)
    DEFAULT_FREQUENCY_PENALTY = config("DEFAULT_FREQUENCY_PENALTY", default="0.0", cast=float)
    DEFAULT_TOP_P = config("DEFAULT_TOP_P", default="1.0", cast=float)
    DEFAULT_CHUNK_LENGTH = config("DEFAULT_CHUNK_LENGTH", default=8192, cast=int)

    # Record connection information during initialization
    def __init__(self):
        logger.info("=== Database connection configuration ===")
        logger.info(f"DB_HOST: {self.DB_HOST}")
        logger.info(f"DB_PORT: {self.DB_PORT}")
        logger.info(f"DB_NAME: {self.DB_NAME}")
        logger.info(f"DB_USER: {self.DB_USER}")
        logger.info(f"DB_PASSWORD: {'*' * len(self.DB_PASSWORD) if self.DB_PASSWORD else 'None'}")
        logger.info("=====================")


env = ENV()  # Singleton
