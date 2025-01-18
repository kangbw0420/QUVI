import uuid
from urllib.parse import quote_plus
from utils.config import Config

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()


def check_session_id(user_id: str, session_id: str) -> bool :
    # session_id가 개발용인지 검증
    if session_id =="DEV_SESSION_ID":
        return 0
    # 일단 session_id만 검증
    command = f"SELECT 1 FROM session WHERE session_id = '{session_id}';"
    # session_status를 체크, active면 True, 그외(completed, error)면 False
    command2 = f"SELECT session_status FROM session  WHERE session_id = '{session_id}';"

    from urllib.parse import quote_plus
    password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
    db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
    engine = create_engine(db_url)

    with engine.begin() as connection:
        # 사용하려는 스키마 지정
        connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

        cursor = connection.execute(text(command))
        if cursor is not None:
            cursor = connection.execute(text(command2))
            for row in cursor.fetchall():
                if row[0] == "active":
                    return 1
                else:
                    return 0

    return 0



def make_session_id(user_id:str) -> str:
    session_id = str(uuid.uuid4())

    password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
    db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
    engine = create_engine(db_url)

    with engine.begin() as connection:
        # 사용하려는 스키마 지정
        connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

        command = text("""
            INSERT INTO session (user_id, session_id, session_status)
            VALUES (:user_id, :session_id, 'active')
        """)
        
        connection.execute(command, {
            'user_id': user_id,
            'session_id': session_id
        })

    return session_id

# (프로덕션 제거) 주석처리여도 됨
def make_dev_session_id(user_id: str, session_id:str) -> str:
    password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
    db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
    engine = create_engine(db_url)
    
    with engine.begin() as connection:
        # 사용하려는 스키마 지정
        connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

        # 먼저 해당 session_id가 존재하는지 확인
        check_command = text("""
            SELECT session_id FROM session WHERE session_id = :session_id
        """)
        result = connection.execute(check_command, {'session_id': session_id}).fetchone()
        
        # 존재하지 않을 때만 INSERT 실행
        if not result:
            command = text("""
                INSERT INTO session (user_id, session_id, session_status)
                VALUES (:user_id, :session_id, 'active')
            """)
            connection.execute(command, {
                'user_id': user_id,
                'session_id': session_id
            })
            
    return session_id

def save_record(session_id:str, analyzed_question:str, answer:str, sql_query:str) -> bool:
    # session_id가 개발용인지 검증
    if session_id =="DEV_SESSION_ID":
        return 0
    password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
    db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
    engine = create_engine(db_url)

    with engine.begin() as connection:
        # 사용하려는 스키마 지정
        connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

        command2 = f"SELECT * FROM record;"
        cursor = connection.execute(text(command2))
        command = text("INSERT INTO record (session_id, last_analyzed_question, last_answer, last_sql_query) VALUES (:session_id, :question, :answer, :query)")
        
        # sql_query에 한글이 있을 경우 SQLAlchemy가 자동으로 적절한 이스케이프 처리를 하도록 params로 저장장
        params = {
            "session_id": session_id,
            "question": analyzed_question,
            "answer": answer,
            "query": sql_query
        }
        cursor = connection.execute(command, params)

    return 0

def extract_last_data(session_id:str) -> list:

    # 최대 3개의 row
    result = []
    command = f"SELECT last_analyzed_question, last_answer, last_sql_query FROM record WHERE session_id = '{session_id}' ORDER BY record_time DESC LIMIT 3;"

    from urllib.parse import quote_plus
    password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
    db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
    engine = create_engine(db_url)

    with engine.begin() as connection:
        # 사용하려는 스키마 지정
        connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

        cursor = connection.execute(text(command))
        result = cursor.fetchall()
    return result
