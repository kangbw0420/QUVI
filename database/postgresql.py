import psycopg2.pool
from psycopg2 import OperationalError, InterfaceError
from psycopg2.extras import RealDictCursor

from api.dto import PostgreToVectorData, MappingRequest
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
        PostgreSQL.pool_data = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_DATABASE,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
    if PostgreSQL.pool_prompt is None:
        PostgreSQL.pool_prompt = psycopg2.pool.SimpleConnectionPool(
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


def get_connection(pool: psycopg2.pool.SimpleConnectionPool):
    """끊어진 연결이 있으면 감지하고, 새로 연결을 가져옴"""
    if pool is None:
        connect_postgresql_pool()

    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")  # 연결 상태 체크
        return conn
    except (OperationalError, InterfaceError):
        print("Connection Failed. Retry...")
        pool.putconn(conn, close=True)  # 기존 연결 폐기
        return pool.getconn()  # 새 연결 가져오기


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




# 전체 Prompt 데이터 리스트를 가져오는 함수
def get_all_prompt():
    query = """
        SELECT *
        FROM (
            SELECT DISTINCT ON (node_nm, prompt_nm) *
            FROM prompt
            WHERE del_yn = 'N'
            ORDER BY node_nm, prompt_nm, version DESC
        ) AS innerQuery
        ORDER BY created_at DESC
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# Prompt 데이터를 가져오는 함수
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


# 새 Prompt 데이터를 삽입하는 함수
def insert_prompt(node_nm: str, prompt_nm: str, prompt: str):
    query = """
        INSERT INTO prompt (
            node_nm,
            prompt_nm,
            prompt,
            version
        ) 
        VALUES (
            %s,
            %s,
            %s,
            (SELECT COALESCE(MAX(version), 0) FROM prompt WHERE node_nm = %s AND prompt_nm = %s) + 0.1
        )
    """
    return query_execute(
        query,
        params=(node_nm, prompt_nm, prompt, node_nm, prompt_nm),
        use_prompt_db=True
    )


# 새 Prompt 데이터를 삭제하는 함수
def delete_prompt(node_nm: str, prompt_nm: str):
    query = """
        UPDATE prompt
        SET del_yn = 'Y' 
        WHERE node_nm = %s
        AND prompt_nm = %s
    """
    return query_execute(
        query,
        params=(node_nm, prompt_nm),
        use_prompt_db=True
    )




# 벡터 전체 데이터를 가져오는 함수
def get_all_data_rdb():
    query = """
        SELECT *
        FROM vector_data
        WHERE del_yn = 'N'
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# 벡터 데이터를 가져오는 함수
def get_data_rdb(title: str):
    query = """
        SELECT *
        FROM vector_data
        WHERE title = %s
        AND del_yn = 'N'
    """
    return query_execute(
        query,
        params=(title,),
        use_prompt_db=True
    )


# 새 벡터 데이터를 삽입하는 함수
def insert_vector_data(data: PostgreToVectorData):
    query = """
        INSERT INTO vector_data (
            title,
            shot,
            id
        )
        VALUES (
            %s,
            %s,
            %s
        )
    """
    return query_execute(
        query,
        params=(data.title, data.shot, data.id),
        use_prompt_db=True
    )


# 벡터 데이터 업데이트 함수
def update_vector_data(data: PostgreToVectorData):
    # 기존 데이터 가져오기
    select_query = """
        SELECT *
        FROM vector_data
        WHERE idx = %s
        AND del_yn = 'N'
    """
    get_data = query_execute(
        select_query,
        params=(data.item_id,),
        use_prompt_db=True
    )

    if get_data:
        get_data = get_data[0]  # 첫 번째 결과를 가져옴
        # 텍스트나 컬렉션명이 다를 경우 업데이트
        if (get_data["data"] != data.document or get_data["document"] != data.collection_name):
            update_query = """
                UPDATE vector_data
                SET data = %s, document = %s, del_yn = 'Y'
                WHERE idx = %s
            """
            return query_execute(
                update_query,
                params=(data.document, data.collection_name, data.item_id),
                use_prompt_db=True
            )


# 벡터 데이터 삭제 처리 함수
def delete_data_rdb(title: str):
    update_query = """
        UPDATE vector_data
        SET del_yn = 'Y'
        WHERE title = %s
    """
    return query_execute(
        update_query,
        params=(title,),
        use_prompt_db=True
    )




# 컬럼명 관리 데이터 전체 조회
def get_all_mapping():
    query = """
        SELECT *
        FROM title_mapping
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# 컬럼명 관리 데이터 추가
def insert_mapping(data: MappingRequest):
    query = """
        INSERT INTO title_mapping (
            original_title,
            replace_title,
            type,
            align
        ) 
        VALUES (
            %s,
            %s,
            %s,
            %s
        )
    """
    return query_execute(
        query,
        params=(data.original_title, data.replace_title, data.type, data.align),
        use_prompt_db=True
    )


# 컬럼명 관리 데이터 수정
def update_mapping(data: MappingRequest):
    query = """
        UPDATE title_mapping
        SET
            original_title = %s,
            replace_title = %s,
            type = %s,
            align = %s
        WHERE
            idx = %s
    """
    return query_execute(
        query,
        params=(data.original_title, data.replace_title, data.type, data.align, data.idx),
        use_prompt_db=True
    )


# 컬럼명 관리 데이터 삭제
def delete_mapping(idx: int):
    query = """
        DELETE
        FROM title_mapping
        WHERE
            idx = %s
    """
    return query_execute(
        query,
        params=([idx]),
        use_prompt_db=True
    )