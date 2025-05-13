import traceback
from urllib.parse import quote_plus
from typing import Union, Sequence, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Result
from sqlalchemy.sql.expression import Executable

from utils.config import Config
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

logger = setup_logger('executor')

qna_manager = QnAManager()

def execute(command: Union[str, Executable], fetch="all") -> Union[Sequence[Dict[str, Any]], Result]:  # type: ignore
    """SQL 쿼리를 실행하고 결과를 반환합니다.
    Returns:
        Union[Sequence[Dict[str, Any]], Result]: 쿼리 실행 결과.
        fetch='all': 모든 결과 행을 딕셔너리 리스트로 반환.
        fetch='one': 첫 번째 결과 행을 딕셔너리로 반환.
        fetch='cursor': 커서 객체 직접 반환.
    Raises:
        ValueError: fetch 파라미터가 유효하지 않은 경우.
        TypeError: command가 문자열이나 Executable이 아닌 경우.
        Exception: 데이터베이스 연결 또는 쿼리 실행 중 오류 발생시.
    """
    try:
        parameters = {}
        execution_options = {}

        logger.info("Setting up database connection")
        # URL encode the password to handle special characters
        password = quote_plus(str(Config.DB_PASSWORD))
        db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"

        engine = create_engine(db_url)

        with engine.begin() as connection:
            # SQLAlchemy를 활용해 실행 가능한 쿼리 객체로 변경
            if isinstance(command, str):
                command = text(command)
            elif isinstance(command, Executable):
                pass
            else:
                err_msg = f"Query expression has unknown type: {type(command)}"
                logger.error(err_msg)
                raise TypeError(err_msg)

            logger.info("Executing query")
            cursor = connection.execute(
                command,
                parameters,
                execution_options=execution_options,
            )
            logger.info("Query execution completed")

            if cursor.returns_rows:
                if fetch == "all":
                    rows = cursor.fetchall()
                    result = [x._asdict() for x in rows]
                elif fetch == "one":
                    first_result = cursor.fetchone()
                    if first_result is None:
                        logger.info("No results found")
                        result = []
                    else:
                        logger.info("Converting single row to dictionary")
                        result = [first_result._asdict()]
                elif fetch == "cursor":
                    logger.info("Returning cursor directly")
                    return cursor
                else:
                    err_msg = f"Invalid fetch mode: {fetch}"
                    logger.error(err_msg)
                    raise ValueError(
                        "Fetch parameter must be either 'one', 'all', or 'cursor'"
                    )

                return result
            else:
                logger.info("Query does not return any rows")
                return []

    except Exception as e:
        logger.error(f"Error executing query: {type(e).__name__}: {str(e)}")
        logger.debug("Detailed traceback:", exc_info=True)
        raise