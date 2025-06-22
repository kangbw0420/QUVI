#!/bin/bash

BASE_DIR="/webRoot/aicfoagent/src"
SERVER_DIR="$BASE_DIR/server_python"
VENV_ACTIVATE="$SERVER_DIR/venv/bin/activate"

# 로그 디렉토리 설정
LOG_DIR="$SERVER_DIR/logs"
SERVER_LOG="$SERVER_DIR/agent.log"

# 기존 프로세스 종료
echo "SERVER 를 종료합니다." | tee -a $SERVER_LOG
pkill -9 -f "python3 main.py --port=8000"
pkill -9 -f "from multiprocessing"

echo "모든 프로세스가 성공적으로 종료되었습니다."
