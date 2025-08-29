#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  Back Agent Docker 이미지 빌드${NC}"
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

# builds 디렉토리 생성
echo -e "${BLUE}builds 디렉토리를 생성합니다...${NC}"
mkdir -p builds

# 기존 컨테이너 중지 및 제거
echo -e "${YELLOW}기존 컨테이너를 정리합니다...${NC}"
$DOCKER_COMPOSE -f docker-compose.build.yml down

# 이미지 빌드
echo -e "${BLUE}Docker 이미지를 빌드합니다...${NC}"
$DOCKER_COMPOSE -f docker-compose.build.yml build

# Docker 이미지를 builds 디렉토리에 저장
echo -e "${BLUE}Docker 이미지를 builds 디렉토리에 저장합니다...${NC}"
IMAGE_NAME="back_agent"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
TAR_FILE="builds/${IMAGE_NAME}-${IMAGE_TAG}.tar"

if docker images | grep -q "${IMAGE_NAME}.*${IMAGE_TAG}"; then
    echo -e "${BLUE}이미지를 tar 파일로 저장 중...${NC}"
    docker save ${FULL_IMAGE_NAME} > ${TAR_FILE}
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Docker 이미지 저장 완료: ${TAR_FILE}${NC}"
        echo -e "${GREEN}✅ 이제 에어갭 환경에서 docker-run.sh로 실행할 수 있습니다!${NC}"
    else
        echo -e "${RED}❌ Docker 이미지 저장 실패!${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker 이미지를 찾을 수 없습니다: ${FULL_IMAGE_NAME}${NC}"
fi

echo ""
echo -e "${GREEN}🎉 빌드 완료!${NC}"
echo -e "${YELLOW}📦 저장된 파일:${NC}"
echo -e "   - ${TAR_FILE}"
echo ""
echo -e "${YELLOW}💡 에어갭 환경에서 실행:${NC}"
echo -e "   1. tar 파일을 에어갭 환경으로 전송"
echo -e "   2. docker load < ${TAR_FILE}"
echo -e "   3. ./docker-run.sh"
