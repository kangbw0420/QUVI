import asyncio
import uvicorn
from fastapi import FastAPI
from api.api import api
from fastapi.middleware.cors import CORSMiddleware
from api.data_api import data_api
app = FastAPI()


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5000", "https://aicfoprm-dev.appplay.co.kr"],  # 프론트엔드 주소
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

app.include_router(api)
app.include_router(data_api, prefix="/data")

if __name__ == "__main__":
    print("\n=== AICFO python 백엔드 시작 ===")
    
    # 이벤트 루프 생성
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # 명시적으로 이벤트 루프 설정

    async def main():
        # FastAPI 서버 실행
        config = uvicorn.Config(
            "main:app", host="0.0.0.0", port=8000, reload=True
        )  # 개발 단계에서는 reload 꺼야 함
        server = uvicorn.Server(config)
        # 서버와 터미널 테스트 병렬 실행
        await asyncio.gather(
            server.serve(),  # FastAPI 서버 실행
            # terminal_test()
        )

    try:
        loop.run_until_complete(main())  # 루프 실행
    except KeyboardInterrupt:
        print("\nShutting down...")