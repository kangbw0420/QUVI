import argparse

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.api import api
from api.data_api import data_api
from api.llmadmin_api import llmadmin_api
from api.mapping_api import mapping_api
from utils.logger import setup_logger

# 애플리케이션 루트 로거 설정
logger = setup_logger('app')

def parse_arguments():
    parser = argparse.ArgumentParser(description="FastAPI Uvicorn Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    return parser.parse_args()

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info(f"{request.client.host} - {request.method} {request.url.path} - {response.status_code}")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5000", "https://aicfoprm-dev.appplay.co.kr"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api, prefix="")
app.include_router(data_api, prefix="/data")
app.include_router(llmadmin_api, prefix="/llmadmin")
app.include_router(mapping_api, prefix="/mapping")

if __name__ == "__main__":
    args = parse_arguments()
    
    # FastAPI의 내부 로깅을 우리의 로깅 설정과 통합
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    uvicorn_log_config["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
        log_config=uvicorn_log_config
    )