import uuid
import json
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from typing import Optional, Dict, Any
from utils.config import Config

class StateManager:
    @staticmethod
    def create_state(chain_id: str, user_question: str) -> str:
        """
        초기 상태 생성
        Returns:
            str: 생성된 state_id
        """
        try:
            state_id = str(uuid.uuid4())
            
            password = quote_plus(str(Config.DB_PASSWORD))
            db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                command = text("""
                    INSERT INTO state (
                        id,
                        chain_id,
                        user_question
                    ) VALUES (
                        :state_id,
                        :chain_id,
                        :user_question
                    )
                """)
                
                connection.execute(command, {
                    'state_id': state_id,
                    'chain_id': chain_id,
                    'user_question': user_question
                })

            return state_id

        except Exception as e:
            print(f"Error in create_state: {str(e)}")
            raise

    @staticmethod
    def update_state(state_id: str, updates: Dict[str, Any]) -> bool:
        """
        상태 업데이트
        Args:
            state_id: 업데이트할 state의 ID
            updates: 업데이트할 필드와 값들의 딕셔너리
        Returns:
            bool: 성공 여부
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD))
            db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
            engine = create_engine(db_url)

            # JSON 데이터 직렬화
            for key, value in updates.items():
                if isinstance(value, (dict, list)):
                    updates[key] = json.dumps(value, ensure_ascii=False)

            # 동적 UPDATE 쿼리 생성
            set_clauses = []
            params = {'state_id': state_id}
            
            for key, value in updates.items():
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

            update_query = text(f"""
                UPDATE state 
                SET {', '.join(set_clauses)}
                WHERE id = :state_id
            """)

            with engine.begin() as connection:
                connection.execute(update_query, params)

            return True

        except Exception as e:
            print(f"Error in update_state: {str(e)}")
            raise

    @staticmethod
    def get_state(state_id: str) -> Optional[Dict[str, Any]]:
        """
        현재 상태 조회
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD))
            db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                command = text("""
                    SELECT * FROM state WHERE id = :state_id
                """)
                
                result = connection.execute(command, {'state_id': state_id}).fetchone()
                
                if result:
                    state_dict = dict(result)
                    # JSON 문자열을 파이썬 객체로 변환
                    for key, value in state_dict.items():
                        if isinstance(value, str):
                            try:
                                state_dict[key] = json.loads(value)
                            except json.JSONDecodeError:
                                pass  # 일반 문자열인 경우 그대로 유지
                    return state_dict
                return None

        except Exception as e:
            print(f"Error in get_state: {str(e)}")
            raise