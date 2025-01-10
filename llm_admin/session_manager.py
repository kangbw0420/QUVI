import uuid
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
    password = quote_plus(str(Config.DB_PASSWORD))
    db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
    engine = create_engine(db_url)

    with engine.begin() as connection:
        cursor = connection.execute(text(command))
        if cursor is not None:
            cursor = connection.execute(text(command2))
            for row in cursor.fetchall():
                if row[0] == "active":
                    return 1
                else:
                    return 0

    return 0



def make_session_id(user_id:str, session_id:str) -> str:
    # session_id가 개발용인지 검증
    if session_id =="DEV_SESSION_ID":
        return session_id
    session_id = str(uuid.uuid4())
        
    from urllib.parse import quote_plus

    password = quote_plus(str(Config.DB_PASSWORD))
    db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
    engine = create_engine(db_url)
    with engine.begin() as connection:
        
        # length관련 코드는 DB의 ID값이 auto가 되면 SQL에서 id를 제외하고 정리할 것
        command2 = f"SELECT * FROM session;"
        cursor = connection.execute(text(command2))
        length = len(cursor.fetchall())
        command = f"INSERT INTO session (id, user_id, session_id, session_status ) VALUES ('{length+1}', '{user_id}','{session_id}' , 'active');"
        
        connection.execute(text(command))

    return session_id

def save_record(session_id:str, analyzed_question:str, answer:str, sql_query:str) -> bool:
    # session_id가 개발용인지 검증
    if session_id =="DEV_SESSION_ID":
        return 0
    from urllib.parse import quote_plus
    password = quote_plus(str(Config.DB_PASSWORD))
    db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
    engine = create_engine(db_url)

    with engine.begin() as connection:

        # length관련 코드는 DB의 ID값이 auto가 되면 SQL에서 id를 제외하고 정리할 것
        command2 = f"SELECT * FROM record;"
        cursor = connection.execute(text(command2))
        length = len(cursor.fetchall())
        command = text("INSERT INTO record (id, session_id, last_analyzed_question, last_answer, last_sql_query) VALUES (:id, :session_id, :question, :answer, :query)")
        
        # sql_query에 한글이 있을 경우 SQLAlchemy가 자동으로 적절한 이스케이프 처리를 하도록 params로 저장장
        params = {
            "id": length+4,
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
    password = quote_plus(str(Config.DB_PASSWORD))
    db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
    engine = create_engine(db_url)

    with engine.begin() as connection:
        cursor = connection.execute(text(command))
        result = cursor.fetchall()
    return result
