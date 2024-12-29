import uvicorn
from fuse.langfuse_server import create_langfuse_app, DbType
import multiprocessing
import os

def run_langfuse():
    db_type = DbType.POSTGRES if os.getenv("PRODUCTION") else DbType.SQLITE
    app = create_langfuse_app(db_type)
    uvicorn.run(app, host="0.0.0.0", port=8001)

def run_main():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    # 멀티프로세싱으로 두 서버 실행
    langfuse_process = multiprocessing.Process(target=run_langfuse)
    main_process = multiprocessing.Process(target=run_main)
    
    try:
        langfuse_process.start()
        main_process.start()
        
        langfuse_process.join()
        main_process.join()
    except KeyboardInterrupt:
        langfuse_process.terminate()
        main_process.terminate()
        print("\nServers stopped")