import threading
import time

from psycopg2 import OperationalError, InterfaceError
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool, ThreadedConnectionPool

from utils.config import Config

# PostgreSQL 클래스 정의
class PostgreSQL:
    host: str = Config.DB_HOST
    port: int = Config.DB_PORT
    database: str = Config.DB_DATABASE
    user: str = Config.DB_USER
    password: str = Config.DB_PASSWORD
    pool_data = None
    pool_prompt = None


# PostgreSQL 연결 풀 생성
def connect_postgresql_pool():
    if PostgreSQL.pool_data is None:
        # PostgreSQL.pool_data = SimpleConnectionPool(
        PostgreSQL.pool_data = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_DATABASE,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
    if PostgreSQL.pool_prompt is None:
        # PostgreSQL.pool_prompt = SimpleConnectionPool(
        PostgreSQL.pool_prompt = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=Config.DB_HOST_PROMPT,
            port=Config.DB_PORT_PROMPT,
            database=Config.DB_DATABASE_PROMPT,  # Prompt용 데이터베이스
            user=Config.DB_USER_PROMPT,
            password=Config.DB_PASSWORD_PROMPT
        )

# PostgreSQL 연결 풀 초기화
connect_postgresql_pool()


# def get_connection(pool: SimpleConnectionPool):
def get_connection(pool: ThreadedConnectionPool):
    """끊어진 연결이 있으면 감지하고, 새로 연결을 가져옴"""
    if pool is None:
        connect_postgresql_pool()

    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1;")  # 연결 상태 체크
        return conn
    except (OperationalError, InterfaceError):
        print("Connection Failed. Retry...")
        pool.putconn(conn, close=True)  # 기존 연결 폐기
        return pool.getconn()  # 새 연결 가져오기


def expire_connections():
    """ 일정 시간이 지나면 연결을 다시 맺도록 만듦 """
    while True:
        time.sleep(300) # 5분마다
        try:
            for _ in range(PostgreSQL.pool_data.maxconn):
                conn = PostgreSQL.pool_data.getconn()
                PostgreSQL.pool_data.putconn(conn, close=True)  # 강제 종료 후 다시 연결
            for _ in range(PostgreSQL.pool_prompt.maxconn):
                conn = PostgreSQL.pool_prompt.getconn()
                PostgreSQL.pool_prompt.putconn(conn, close=True)  # 강제 종료 후 다시 연결
            # print("Connection pool refreshed")
        except Exception as e:
            print(f"Connection pool refresh error : {e}")

# 백그라운드에서 실행
threading.Thread(target=expire_connections, daemon=True).start()


# 쿼리를 실행하는 일반 함수
def execute_query(query):
    return query_execute(query)


# 일반 쿼리 실행 함수
def query_execute(query, params=None, use_prompt_db=False):
    connection = None
    pool = None
    try:
        # 사용하려는 데이터베이스 풀 선택
        pool = PostgreSQL.pool_prompt if use_prompt_db else PostgreSQL.pool_data
        # connection = pool.getconn()  # 선택된 풀에서 연결 가져오기
        connection = get_connection(pool)  # 선택된 풀에서 연결 가져오기
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        # 사용하려는 스키마 지정
        schema = Config.DB_SCHEMA_PROMPT if use_prompt_db else Config.DB_SCHEMA
        cursor.execute("SET search_path TO '%s'" % schema)

        # 쿼리 실행
        cursor.execute(query, params if params else ())

        # SELECT 쿼리라면 결과 반환
        if query.strip().upper().startswith("SELECT"):
            return cursor.fetchall()
        # voc_list INSERT 쿼리라면 신규row 의 seq 반환
        elif query.strip().upper().startswith("INSERT INTO voc_list"):
            result = cursor.fetchone()
            if result is None:
                raise
            connection.commit()
            cursor.close()
            return result['seq']

        connection.commit()
        cursor.close()
        return True
    except Exception as error:
        print(f"Error executing query: {error}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            pool.putconn(connection)

def get_prompt(node_nm: str, prompt_nm: str):
    query = """
        SELECT *
        FROM prompt
        WHERE node_nm = %s
        AND prompt_nm = %s
        AND version = (
            SELECT MAX(version)
            FROM prompt
            WHERE node_nm = %s
            AND prompt_nm = %s
        )
        AND del_yn = 'N'
    """
    return query_execute(
        query,
        params=(node_nm, prompt_nm, node_nm, prompt_nm),
        use_prompt_db=True
    )