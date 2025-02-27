import threading
import time

from psycopg2 import OperationalError, InterfaceError
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool, ThreadedConnectionPool

from api.dto import PostgreToVectorData, MappingRequest, VocRequest, RecommendRequest, RecommendCtgryRequest, \
    StockRequest
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
def get_all_fewshot_rdb():
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
def get_fewshot_rdb(title: str):
    query = """
        SELECT *
        FROM vector_data
        WHERE del_yn = 'N'
        AND title = %s
    """
    return query_execute(
        query,
        params=(title,),
        use_prompt_db=True
    )


# 새 벡터 데이터를 삽입하는 함수
def insert_fewshot_rdb(data: PostgreToVectorData):
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


# 벡터 데이터 삭제 처리 함수
def delete_fewshot_rdb(title: str):
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
        SELECT
            idx,
            original_title,
            replace_title,
            type,
            align,
            TO_CHAR(reg_dtm, 'YYYY-MM-DD HH24:MI:SS') AS reg_dtm
        FROM title_mapping
        ORDER BY idx
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# 컬럼명 관리 데이터 단건 조회
def get_mapping(idx: int):
    query = """
        SELECT *
        FROM title_mapping
        WHERE idx = %s
    """
    return query_execute(
        query,
        params=(idx,),
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
        params=(data.originalTitle, data.replaceTitle, data.type, data.align),
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
        params=(data.originalTitle, data.replaceTitle, data.type, data.align, data.idx),
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
        params=(idx,),
        use_prompt_db=True
    )




# VOC 데이터 전체 조회
def get_all_voc():
    query = """
        SELECT
            seq,
            user_id,
            company_id,
            channel,
            utterance_contents,
            conversation_id,
            chain_id,
            type,
            image_url,
            content,
            answer,
            TO_CHAR(regist_datetime, 'YYYY-MM-DD HH24:MI:SS') AS regist_datetime,
            TO_CHAR(answer_datetime, 'YYYY-MM-DD HH24:MI:SS') AS answer_datetime
        FROM voc_list
        ORDER BY seq DESC
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# VOC 데이터 단건 조회
def get_voc(seq: int):
    query = """
        SELECT *
        FROM voc_list
        WHERE seq = %s
    """
    return query_execute(
        query,
        params=(seq,),
        use_prompt_db=True
    )


# VOC 데이터 추가
def insert_voc(data: VocRequest):
    query = """
        INSERT INTO voc_list (
            user_id,
            use_intt_id,
            company_id,
            channel,
            utterance_contents,
            conversation_id,
            chain_id,
            type,
            content
        ) 
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        RETURNING seq
    """
    return query_execute(
        query,
        params=(data.userId, data.useInttId, data.companyId, data.channel, data.utteranceContents, data.conversationId, data.chainId, data.type, data.content),
        use_prompt_db=True
    )


# VOC 데이터 수정
def update_voc(data: VocRequest):
    query = """
        UPDATE voc_list
        SET
            image_url = %s
        WHERE
            seq = %s
    """
    return query_execute(
        query,
        params=(data.imageUrl, data.seq),
        use_prompt_db=True
    )


# VOC 데이터 삭제
def delete_voc(seq: int):
    query = """
        DELETE
        FROM voc_list
        WHERE
            seq = %s
    """
    return query_execute(
        query,
        params=(seq,),
        use_prompt_db=True
    )


# VOC 데이터의 답변 업데이트
def answer_voc(data: VocRequest):
    query = """
        UPDATE voc_list
        SET
            answer = %s,
            answer_datetime = NOW()
        WHERE
            seq = %s
    """
    return query_execute(
        query,
        params=(data.answer, data.seq),
        use_prompt_db=True
    )




# 홈 화면 추천질의 데이터 조회
def get_home_recommend():
    query = """
        SELECT
            r.ctgry_cd AS ctgryCd,
            r.ctgry_nm AS ctgryNm,
            r.img_path AS imgPath,
            STRING_AGG(c.recommend_quest, '|' ORDER BY c.order_by) AS recommendQuest
        FROM ctgry_code r
        LEFT JOIN recommend_quest c
        ON (r.ctgry_cd = c.ctgry_cd)
        GROUP BY r.ctgry_cd, r.ctgry_nm, r.img_path
        ORDER BY r.order_by ASC
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# 추천질의 데이터 전체 조회
def get_all_recommend():
    query = """
        SELECT *
        FROM recommend_quest
        ORDER BY order_by ASC
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# 추천질의 데이터 단건 조회
def get_recommend(seq: int):
    query = """
        SELECT *
        FROM recommend_quest
        WHERE recommend_quest_seq = %s
    """
    return query_execute(
        query,
        params=(seq,),
        use_prompt_db=True
    )


# 추천질의 데이터 추가
def insert_recommend(data: RecommendRequest):
    query = """
        INSERT INTO recommend_quest (
            ctgry_cd,
            recommend_quest,
            order_by,
            use_yn
        ) 
        VALUES (
            %s,
            %s,
            (SELECT COALESCE(MAX(order_by), 0) FROM recommend_quest WHERE ctgry_cd = %s) + 1,
            %s
        )
    """
    return query_execute(
        query,
        params=(data.ctgryCd, data.recommendQuest, data.ctgryCd, data.useYn),
        use_prompt_db=True
    )


# 추천질의 데이터 수정
def update_recommend(data: RecommendRequest):
    query = """
        UPDATE recommend_quest
        SET
            ctgry_cd = %s,
            recommend_quest = %s,
            order_by = %s,
            use_yn = %s
        WHERE
            recommend_quest_seq = %s
    """
    return query_execute(
        query,
        params=(data.ctgryCd, data.recommendQuest, data.orderBy, data.useYn, data.seq),
        use_prompt_db=True
    )


# 추천질의 데이터 삭제
def delete_recommend(seq: int):
    query = """
        DELETE
        FROM recommend_quest
        WHERE
            recommend_quest_seq = %s
    """
    return query_execute(
        query,
        params=(seq,),
        use_prompt_db=True
    )




# 추천질의 카테고리 데이터 전체 조회
def get_all_recommend_ctgry():
    query = """
        SELECT *
        FROM ctgry_code
        ORDER BY order_by ASC
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# 추천질의 카테고리 데이터 단건 조회
def get_recommend_ctgry(ctgryCd: str):
    query = """
        SELECT *
        FROM ctgry_code
        WHERE ctgry_cd = %s
    """
    return query_execute(
        query,
        params=(ctgryCd,),
        use_prompt_db=True
    )


# 추천질의 카테고리 데이터 추가
def insert_recommend_ctgry(data: RecommendCtgryRequest):
    query = """
        INSERT INTO ctgry_code (
            ctgry_cd,
            ctgry_nm,
            img_path,
            order_by
        ) 
        VALUES (
            %s,
            %s,
            %s,
            (SELECT COALESCE(MAX(order_by), 0) FROM ctgry_code) + 1
        )
    """
    return query_execute(
        query,
        params=(data.ctgryCd, data.ctgryNm, data.imgPath),
        use_prompt_db=True
    )


# 추천질의 카테고리 데이터 수정
def update_recommend_ctgry(data: RecommendCtgryRequest):
    query = """
        UPDATE ctgry_code
        SET
            ctgry_nm = %s,
            img_path = %s,
            order_by = %s,
            updated_at = NOW()
        WHERE
            ctgry_cd = %s
    """
    return query_execute(
        query,
        params=(data.ctgryNm, data.imgPath, data.orderBy, data.ctgryCd),
        use_prompt_db=True
    )


# 추천질의 카테고리 데이터 삭제
def delete_recommend_ctgry(ctgryCd: str):
    query = """
        DELETE
        FROM ctgry_code
        WHERE
            ctgry_cd = %s
    """
    return query_execute(
        query,
        params=(ctgryCd,),
        use_prompt_db=True
    )




# 주식명 유의어 데이터 전체 조회
def get_all_stock():
    query = """
        SELECT
            stock_cd,
            stock_nm,
            STRING_AGG(stock_nick_nm, ',') AS stock_nick_nm
        FROM stockname
        GROUP BY stock_cd, stock_nm
        ORDER BY stock_cd ASC
    """
    return query_execute(
        query,
        params=(),
        use_prompt_db=True
    )


# 주식명 유의어 데이터 단건 조회
def get_stock(stockCd: str):
    query = """
        SELECT
            stock_cd,
            stock_nm,
            STRING_AGG(stock_nick_nm, ',') AS stock_nick_nm
        FROM stockname
        WHERE stock_cd = %s
        GROUP BY stock_cd, stock_nm
    """
    return query_execute(
        query,
        params=(stockCd,),
        use_prompt_db=True
    )


# 주식명 유의어 관리 데이터 추가
def insert_stock(data: StockRequest):
    query = """
        INSERT INTO stockname (
            stock_cd,
            stock_nm,
            stock_nick_nm
        ) 
        VALUES (
            %s,
            %s,
            %s
        )
        RETURNING seq
    """
    return query_execute(
        query,
        params=(data.stockCd, data.stockNm, data.stockNickNm),
        use_prompt_db=True
    )


# 주식명 유의어 관리 데이터 삭제
def delete_stock(stockCd: str):
    query = """
        DELETE
        FROM stockname
        WHERE
            stock_cd = %s
    """
    return query_execute(
        query,
        params=(stockCd),
        use_prompt_db=True
    )