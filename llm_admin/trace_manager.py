import uuid
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from utils.config import Config

class TraceManager:

    def create_trace(chain_id: str, node_type: str) -> str:
        """
        노드 실행 시작 시 trace 기록 생성
        Args:
            chain_id: 연관된 체인 ID
            node_type: 노드 타입
        Returns:
            str: 생성된 trace_id
        """
        try:
            trace_id = str(uuid.uuid4())
            
            password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
            db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                # 사용하려는 스키마 지정
                connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

                command = text("""
                    INSERT INTO trace (
                        id,
                        chain_id,
                        node_type,
                        trace_status
                    ) VALUES (
                        :trace_id,
                        :chain_id,
                        :node_type,
                        'active'
                    )
                """)
                
                connection.execute(command, {
                    'trace_id': trace_id,
                    'chain_id': chain_id,
                    'node_type': node_type
                })

            return trace_id

        except Exception as e:
            print(f"Error in create_trace: {str(e)}")
            raise

    def complete_trace(trace_id: str) -> bool:
        """
        노드 실행 완료 시 trace 상태 업데이트
        Args:
            trace_id: 대상 trace ID
        Returns:
            bool: 성공 여부
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
            db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                # 사용하려는 스키마 지정
                connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

                command = text("""
                    UPDATE trace 
                    SET 
                        trace_end = CURRENT_TIMESTAMP,
                        trace_status = 'completed'
                    WHERE id = :trace_id
                """)
                
                connection.execute(command, {
                    'trace_id': trace_id
                })

            return True

        except Exception as e:
            print(f"Error in complete_trace: {str(e)}")
            raise

    def mark_trace_error(trace_id: str) -> bool:
        """
        trace 상태를 error로 변경하고 종료 시간 기록
        Args:
            trace_id: 대상 trace ID
        Returns:
            bool: 성공 여부
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
            db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                # 사용하려는 스키마 지정
                connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

                command = text("""
                    UPDATE trace 
                    SET 
                        trace_end = CURRENT_TIMESTAMP,
                        trace_status = 'error'
                    WHERE id = :trace_id
                """)
                
                connection.execute(command, {
                    'trace_id': trace_id
                })

            return True

        except Exception as e:
            print(f"Error in mark_trace_error: {str(e)}")
            raise