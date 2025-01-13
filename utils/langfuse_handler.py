from langfuse.callback import CallbackHandler
from utils.config import Config

# 환경변수에서 설정 가져오기
langfuse_handler = CallbackHandler(
    host=Config.LANGFUSE_HOST,        # http://localhost:3000
    public_key=Config.LANGFUSE_PUBLIC_KEY,
    secret_key=Config.LANGFUSE_SECRET_KEY
)