#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  Back Agent Docker 실행${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""

# Docker가 설치되어 있는지 확인
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# Docker Compose가 설치되어 있는지 확인 (최신 버전 지원)
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# Docker Compose 명령어 결정
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# 이미지 존재 여부 확인
if ! docker images | grep -q "back_agent.*latest"; then
    echo -e "${RED}back_agent:latest 이미지가 없습니다.${NC}"
    echo -e "${YELLOW}💡 먼저 docker-build.sh를 실행하여 이미지를 준비하세요.${NC}"
    exit 1
fi

# builds 디렉토리 생성
echo -e "${BLUE}builds 디렉토리를 생성합니다...${NC}"
mkdir -p builds

# 기존 컨테이너 중지 및 제거
echo -e "${YELLOW}기존 컨테이너를 정리합니다...${NC}"
$DOCKER_COMPOSE -f docker-compose.run.yml down

# 컨테이너 실행
echo -e "${GREEN}컨테이너를 시작합니다...${NC}"
$DOCKER_COMPOSE -f docker-compose.run.yml up -d

# 컨테이너 상태 확인
echo -e "${BLUE}컨테이너 상태를 확인합니다...${NC}"
$DOCKER_COMPOSE -f docker-compose.run.yml ps

echo ""
echo -e "${GREEN}✅ Back Agent 컨테이너가 시작되었습니다!${NC}"
echo -e "${YELLOW}📝 사용법:${NC}"
echo -e "   - 로그 확인: $DOCKER_COMPOSE -f docker-compose.run.yml logs -f"
echo -e "   - 컨테이너 중지: $DOCKER_COMPOSE -f docker-compose.run.yml down"
echo -e "   - 컨테이너 재시작: $DOCKER_COMPOSE -f docker-compose.run.yml restart"
echo -e "   - 소스 코드 수정 후 자동으로 재빌드됩니다"
