#!/bin/bash

BASE_DIR="/home/was/daquv"

FRONT_DIR="$BASE_DIR/aicfo_prompt_admin_front"
SERVER_DIR="$BASE_DIR/server_python"
VENV_ACTIVATE="$SERVER_DIR/venv/bin/activate"

# 로그 디렉토리 설정
LOG_DIR="$BASE_DIR/logs"
FRONT_LOG="$BASE_DIR/logs/front.log"
SERVER_LOG="$LOG_DIR/agent.log"

# 로그 디렉토리가 없으면 생성
mkdir -p $LOG_DIR

echo $VENV_ACTIVATE
source $VENV_ACTIVATE

# 백그라운드에서 python3 을 실행하고 로그에 출력
cd $SERVER_DIR
echo "python3 를 실행합니다." | tee -a $SERVER_LOG

LOG_DIR=$LOG_DIR nohup python3 main.py --port=8000 --workers=4 &
PYTHON_PID=$!
echo "python3 가 PID $PYTHON_PID 으로 시작되었습니다." | tee -a $SERVER_LOG


# 백그라운드에서 npm 실행하고 로그에 출력
cd $FRONT_DIR
echo "npm 을 실행합니다." | tee -a $FRONT_LOG

nohup npm run dev -- --port 5000 >> $FRONT_LOG 2>&1 &
NPM_PID=$!
echo "npm 이 PID $NPM_PID 으로 시작되었습니다." | tee -a $FRONT_LOG

echo "모든 프로세스가 성공적으로 실행되었습니다."
