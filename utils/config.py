import os

from dotenv import load_dotenv


# .env 파일의 환경 변수 로드
load_dotenv()


class Config:

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_DATABASE = os.getenv("DB_DATABASE")
    DB_SCHEMA = os.getenv("DB_SCHEMA")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    DB_HOST_PROMPT = os.getenv("DB_HOST_PROMPT")
    DB_PORT_PROMPT = os.getenv("DB_PORT_PROMPT")
    DB_DATABASE_PROMPT = os.getenv("DB_DATABASE_PROMPT")
    DB_SCHEMA_PROMPT = os.getenv("DB_SCHEMA_PROMPT")
    DB_USER_PROMPT = os.getenv("DB_USER_PROMPT")
    DB_PASSWORD_PROMPT = os.getenv("DB_PASSWORD_PROMPT")

    API_URL = os.getenv("API_URL")

    VECTOR_STORE_DOMAIN = os.getenv("VECTOR_STORE_DOMAIN")

    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")