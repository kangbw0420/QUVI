#!/bin/bash

BASE_DIR="/home/was/daquv"

# 로그 디렉토리 설정
LOG_DIR="$BASE_DIR/logs"
SERVER_LOG="$LOG_DIR/server.log"
SERVER2_LOG="$LOG_DIR/server2.log"

# 기존 프로세스 종료
echo "SERVER 를 종료합니다." | tee -a $SERVER_LOG
pkill -9 -f "python3 main.py --port=8000"
pkill -9 -f "from multiprocessing"

echo "SERVER 를 종료합니다." | tee -a $SERVER2_LOG
pkill -9 -f "python3 main.py --port=8001"

echo "모든 프로세스가 성공적으로 종료되었습니다."