import os

from dotenv import load_dotenv


# .env 파일의 환경 변수 로드
load_dotenv()


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

    API_URL = os.getenv("API_URL")

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_DATABASE = os.getenv("DB_DATABASE")
    DB_DATABASE_PROMPT = os.getenv("DB_DATABASE_PROMPT")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    
    VECTOR_STORE_DOMAIN = os.getenv("VECTOR_STORE_DOMAIN")
