import asyncio
import uvicorn
import logging
from fastapi import FastAPI, Request
from api.api import api
from api.data_api import data_api
from api.llmadmin_api import llmadmin_api
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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

app.include_router(api)
app.include_router(data_api, prefix="/data")
app.include_router(llmadmin_api, prefix="/llmadmin")

if __name__ == "__main__":
    # 이벤트 루프 생성
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop) # 명시적으로 이벤트 루프 설정
    '''
    async def main():
        # FastAPI 서버 실행
        config = uvicorn.Config(
            "main:app", host="0.0.0.0", port=8000, reload=True
        )  # 개발 단계에서는 reload 꺼야 함
        server = uvicorn.Server(config)
        # 서버와 터미널 테스트 병렬 실행
        await asyncio.gather(
            server.serve(),  # FastAPI 서버 실행
        )
    '''

    config = uvicorn.Config(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

    try:
        # loop.run_until_complete(main()) # 루프 실행
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down...")