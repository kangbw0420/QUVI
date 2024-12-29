import psycopg2.pool
from psycopg2.extras import RealDictCursor
from utils.config import Config
from data_class.request import PostgreToVectorData


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
        PostgreSQL.pool_data = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=PostgreSQL.host,
            port=PostgreSQL.port,
            database=PostgreSQL.database,
            user=PostgreSQL.user,
            password=PostgreSQL.password
        )
    if PostgreSQL.pool_prompt is None:
        PostgreSQL.pool_prompt = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=PostgreSQL.host,
            port=PostgreSQL.port,
            database=Config.DB_DATABASE_PROMPT,  # Prompt용 데이터베이스
            user=PostgreSQL.user,
            password=PostgreSQL.password
        )


# 일반 쿼리 실행 함수
def query_execute(query, params=None, use_prompt_db=False):
    connection = None
    pool = None
    try:
        # 사용하려는 데이터베이스 풀 선택
        pool = PostgreSQL.pool_prompt if use_prompt_db else PostgreSQL.pool_data
        connection = pool.getconn()  # 선택된 풀에서 연결 가져오기
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params if params else ())  # 쿼리 실행
        # SELECT 쿼리라면 결과 반환
        if query.strip().upper().startswith("SELECT"):
            return cursor.fetchall()
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


# Prompt 데이터를 가져오는 함수
def get_prompt(prompt_name: str):
    query = "SELECT * FROM prompt WHERE prompt_name = %s AND version = (SELECT MAX(version) FROM prompt)"
    return query_execute(query, params=(prompt_name,), use_prompt_db=True)


# 새 Prompt 데이터를 삽입하는 함수
def insert_prompt(prompt_name: str, prompt: str):
    query = """
        INSERT INTO prompt (prompt_name, prompt, version) 
        VALUES (%s, %s, (SELECT COALESCE(MAX(version), 0) FROM prompt) + 0.1)
    """
    return query_execute(query, params=(prompt_name, prompt), use_prompt_db=True)


# 벡터 데이터를 가져오는 함수
def get_vector_data(data: PostgreToVectorData):
    if data.type == 'C' and data.collection_name is not None:
        return query_execute(
            "SELECT * FROM vector_data WHERE collection_name = %s",
            params=(data.collection_name,)
        )
    elif data.type == 'I' and data.item_id is not None:
        return query_execute(
            "SELECT * FROM vector_data WHERE idx = %s",
            params=(data.item_id,)
        )
    else:
        raise ValueError("Invalid vector data type or missing parameter")


# 새 벡터 데이터를 삽입하는 함수
def insert_vector_data(data: PostgreToVectorData):
    query = "INSERT INTO vector_data (data, document) VALUES (%s, %s)"
    return query_execute(query, params=(data.text, data.collection_name))


# 벡터 데이터 업데이트 함수
def update_vector_data(data: PostgreToVectorData):
    # 기존 데이터 가져오기
    get_data = query_execute(
        "SELECT * FROM vector_data WHERE idx = %s",
        params=(data.item_id,)
    )
    if get_data:
        get_data = get_data[0]  # 첫 번째 결과를 가져옴
        # 텍스트나 컬렉션명이 다를 경우 업데이트
        if (get_data["data"] != data.text or get_data["document"] != data.collection_name):
            update_query = """
                UPDATE vector_data
                SET data = %s, document = %s
                WHERE idx = %s
            """
            return query_execute(update_query, params=(data.text, data.collection_name, data.item_id))


# 쿼리를 실행하는 일반 함수
def execute_query(query):
    return query_execute(query)


# PostgreSQL 연결 풀 초기화
connect_postgresql_pool()
