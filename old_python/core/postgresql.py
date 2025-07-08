import threading
import time

from psycopg2 import OperationalError, InterfaceError
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger('postgresql')

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


def get_connection(pool: ThreadedConnectionPool):
    """끊어진 연결이 있으면 감지하고, 새로 연결을 가져옴"""
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1;")  # 연결 상태 체크
        return conn
    except (OperationalError, InterfaceError):
        logger.error("Connection Failed. Retry...")
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
        except Exception as e:
            logger.error(f"Connection pool refresh error : {e}")

# 백그라운드에서 실행
threading.Thread(target=expire_connections, daemon=True).start()

# 일반 쿼리 실행 함수
def query_execute(query, params=None, use_prompt_db=True):
    connection = None
    pool = None
    
    from utils.profiler import profiler
    request_id = profiler.get_current_request()
    start_time = time.time()
    
    try:
        # 사용하려는 데이터베이스 풀 선택
        pool = PostgreSQL.pool_prompt if use_prompt_db else PostgreSQL.pool_data

        connection = get_connection(pool)  # 선택된 풀에서 연결 가져오기
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # SELECT 쿼리라면 결과 반환
        if query.strip().upper().startswith(("SELECT", "WITH")):
            result = cursor.fetchall()
            connection.commit()
            cursor.close()
            
            # 프로파일링 시간 기록
            elapsed_time = time.time() - start_time
            if request_id:
                profiler.record_db_call(request_id, elapsed_time, use_prompt_db)
                
            return result
        # INSERT 쿼리에서 RETURNING 절이 있다면 결과 반환
        elif "RETURNING" in query.upper():
            result = cursor.fetchone()
            connection.commit()
            cursor.close()
            
            # 프로파일링 시간 기록
            elapsed_time = time.time() - start_time
            if request_id:
                profiler.record_db_call(request_id, elapsed_time, use_prompt_db)
                
            return result

        connection.commit()
        cursor.close()

        elapsed_time = time.time() - start_time
        if request_id:
            profiler.record_db_call(request_id, elapsed_time, use_prompt_db)

        return True
    except OperationalError as e:
        # 예외가 발생해도 프로파일링 시간 기록
        elapsed_time = time.time() - start_time
        if request_id:
            profiler.record_db_call(request_id, elapsed_time, use_prompt_db)
        logger.error(f"OperationalError: {e}")
        raise
    except InterfaceError as e:
        # 예외가 발생해도 프로파일링 시간 기록
        elapsed_time = time.time() - start_time
        if request_id:
            profiler.record_db_call(request_id, elapsed_time, use_prompt_db)
        logger.error(f"InterfaceError: {e}")
        raise
    except Exception as error:
        # 예외가 발생해도 프로파일링 시간 기록
        elapsed_time = time.time() - start_time
        if request_id:
            profiler.record_db_call(request_id, elapsed_time, use_prompt_db)
        logger.error(f"Error executing query: {error}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            pool.putconn(connection)