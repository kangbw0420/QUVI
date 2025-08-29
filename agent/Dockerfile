FROM maven:3.8-openjdk-8

WORKDIR /home/kjbank/daquv/qv_kjbank/agent

# Maven 캐시 디렉토리 생성
RUN mkdir -p /root/.m2

# pom.xml과 소스 코드를 컨테이너에 복사(빌드를 한 번 해보고 필요한 의존성과 플러그인을 찾아야 함)
COPY pom.xml .
COPY src/ ./src/

# 실제 빌드를 한 번 실행하여 모든 의존성과 플러그인을 다운로드
RUN mvn clean package -DskipTests -B

# 소스 코드 디렉토리 생성 (볼륨 마운트용)
RUN mkdir -p src

EXPOSE 8004

# clean 대신 오프라인 모드 사용
CMD ["sh", "-c", "mvn package -DskipTests -o && java -jar /home/kjbank/daquv/qv_kjbank/agent/target/quvi-agent-1.0.0.jar"]
