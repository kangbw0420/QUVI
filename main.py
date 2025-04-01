import os
import argparse
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from core.api import api
from core.postgresql import connect_postgresql_pool
from utils.logger import setup_logger

# 로그 디렉토리 설정
log_dir = os.environ.get('LOG_DIR', 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 애플리케이션 루트 로거 설정
logger = setup_logger('main')


def parse_arguments():
    parser = argparse.ArgumentParser(description="FastAPI Uvicorn Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    return parser.parse_args()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 로깅
    logger.info("Application startup")

    try:
        # postgresql 커넥션풀 연결
        connect_postgresql_pool()
        logger.info("PostgreSQL connection pool initialized")

        # InMemory 캐시 초기화
        FastAPICache.init(InMemoryBackend())
        logger.info("FastAPI Cache initialized")

        yield
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise
    finally:
        # 애플리케이션 종료 로깅
        logger.info("Application shutdown")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # 요청 시작 로깅
    logger.info(f"Request started - {request.client.host} - {request.method} {request.url.path}")

    try:
        response = await call_next(request)

        # 처리 시간 계산 및 요청 완료 로깅
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed - {request.client.host} - {request.method} {request.url.path} - "
            f"{response.status_code} - {process_time:.2f}ms"
        )

        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            f"Request failed - {request.client.host} - {request.method} {request.url.path} - "
            f"{str(e)} - {process_time:.2f}ms"
        )
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api, prefix="")

if __name__ == "__main__":
    args = parse_arguments()
    
    # FastAPI의 내부 로깅을 우리의 로깅 설정과 통합
    uvicorn_log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",  # 🔥 핵심
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["default"],
            "level": "INFO",
        },
    }

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
        log_config=uvicorn_log_config
    )