#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  Spring Boot Build Only${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""

# 프로필 선택
echo -e "${YELLOW}빌드할 프로필을 선택하세요:${NC}"
echo "1) daquv"
echo "2) dev"
echo "3) prod"
echo ""
read -p "선택 (1-3): " choice

case $choice in
    1)
        PROFILE="daquv"
        ;;
    2)
        PROFILE="dev"
        ;;
    3)
        PROFILE="prod"
        ;;
    *)
        echo -e "${RED}잘못된 선택입니다. 1, 2, 3 중에서 선택해주세요.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}선택된 프로필: $PROFILE${NC}"
echo ""

# Maven이 설치되어 있는지 확인
if ! command -v mvn &> /dev/null; then
    echo -e "${RED}Maven이 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# 애플리케이션 빌드
echo -e "${BLUE}애플리케이션을 빌드합니다...${NC}"
mvn clean package

# 빌드 성공 확인
if [ $? -ne 0 ]; then
    echo -e "${RED}빌드에 실패했습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}빌드가 완료되었습니다.${NC}"
echo ""

# target 디렉토리 확인
echo -e "${BLUE}target 디렉토리 내용:${NC}"
if [ -d "target" ]; then
    ls -la target/*.jar 2>/dev/null || echo "JAR 파일이 없습니다."
    echo ""
else
    echo -e "${RED}target 디렉토리가 존재하지 않습니다.${NC}"
    exit 1
fi

# JAR 파일 찾기
JAR_FILE=$(find target -name "*.jar" -not -name "*sources.jar" -not -name "*javadoc.jar" -not -name "*original*.jar" | head -1)

if [ -z "$JAR_FILE" ]; then
    echo -e "${RED}실행 가능한 JAR 파일을 찾을 수 없습니다.${NC}"
    echo -e "${YELLOW}target 디렉토리의 모든 JAR 파일:${NC}"
    find target -name "*.jar" -type f
else
    echo -e "${GREEN}생성된 JAR 파일: $JAR_FILE${NC}"
    echo -e "${BLUE}파일 크기: $(du -h $JAR_FILE | cut -f1)${NC}"
    echo ""
    echo -e "${YELLOW}실행 방법:${NC}"
    echo -e "${GREEN}java -jar -Dspring.profiles.active=$PROFILE $JAR_FILE${NC}"
fi

echo ""
echo -e "${GREEN}빌드 완료!${NC}"