#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  Spring Boot Build & Run${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""

# 프로필 선택
echo -e "${YELLOW}실행할 프로필을 선택하세요:${NC}"
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

CONFIG_PATH="src/main/resources/profile/$PROFILE/"
CONFIG_FILE="$CONFIG_PATH/application.yml"

# 설정 파일 존재 확인
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}설정 파일을 찾을 수 없습니다: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}다음 경로에 application.yml 파일이 있는지 확인해주세요: $CONFIG_PATH${NC}"
    exit 1
fi

echo -e "${BLUE}설정 파일: $CONFIG_FILE${NC}"
echo ""

# JAR 파일 찾기
JAR_FILE=$(find target -name "*.jar" -not -name "*sources.jar" -not -name "*javadoc.jar" | head -1)

if [ -z "$JAR_FILE" ]; then
    echo -e "${RED}JAR 파일을 찾을 수 없습니다.${NC}"
    echo -e "${YELLOW}target 폴더에 JAR 파일이 있는지 확인해주세요.${NC}"
    exit 1
fi

echo -e "${GREEN}백그라운드에서 애플리케이션을 시작합니다...${NC}"
echo -e "${BLUE}JAR 파일: $JAR_FILE${NC}"
echo -e "${BLUE}Profile: $PROFILE${NC}"

# JVM 옵션 구성 (JDK 버전에 따라 --add-opens 적용)
# java.specification.version 값 사용: 1.8 -> 8, 그 외(11,17,21 등) 그대로 사용
JAVA_SPEC_VER=$(java -XshowSettings:properties -version 2>&1 | awk -F'=' '/java.specification.version/{gsub(/ /,"",$2);print $2}')
JAVA_MAJOR="${JAVA_SPEC_VER%%.*}"
if [ -z "$JAVA_MAJOR" ]; then
    # fallback: "java version \"x.y.z\"" 형태 파싱
    JAVA_MAJOR=$(java -version 2>&1 | awk -F'[".]' '/version/ {print $2}')
fi
if [ "$JAVA_MAJOR" = "1" ]; then
    JAVA_MAJOR=8
fi

echo -e "${BLUE}Detected Java major version: $JAVA_MAJOR${NC}"

JVM_OPTS="-Dspring.profiles.active=$PROFILE"
JVM_OPTS="$JVM_OPTS -Dspring.config.location=classpath:/,$CONFIG_PATH"
JVM_OPTS="-Dspring.profiles.active=$PROFILE -Djava.net.preferIPv4Stack=true"
if [ "$JAVA_MAJOR" -ge 9 ] 2>/dev/null; then
    JVM_OPTS="$JVM_OPTS --add-opens=java.base/java.nio=org.apache.arrow.memory.core,ALL-UNNAMED"
fi

# 백그라운드 실행
nohup java $JVM_OPTS -jar "$JAR_FILE" > ../back.log 2>&1 &
NEW_PID=$!

echo -e "${GREEN}애플리케이션이 백그라운드에서 시작되었습니다.${NC}"
echo -e "${BLUE}새 PID: $NEW_PID${NC}"
echo ""

# 잠시 대기 후 로그 시작 부분 보여주기
sleep 2
echo -e "${YELLOW}=== 애플리케이션 시작 로그 ===${NC}"
head -20 ../back.log
echo ""
echo -e "${GREEN}실시간 로그를 보려면: ${BLUE}tail -f ../back.log${NC}"