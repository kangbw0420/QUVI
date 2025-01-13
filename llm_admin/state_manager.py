from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import json
from typing import Dict, Any, Optional
from decimal import Decimal
from utils.config import Config

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class StateManager:
    @staticmethod
    def update_state(chain_id: str, updates: Dict[str, Any]) -> bool:
        """
        chain_id에 대한 새로운 state를 생성
        Args:
            chain_id: 체인 ID
            updates: 업데이트된 필드와 값들의 딕셔너리
        Returns:
            bool: 성공 여부
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
            db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
                
                # 현재 state의 모든 필드 값을 가져옴
                current_state = StateManager.get_latest_state(connection, chain_id)
                if current_state:
                    # 이전 상태에 새로운 업데이트를 적용
                    new_state = {**current_state, **updates}
                else:
                    new_state = updates

                # JSON 필드 처리
                params = {'chain_id': chain_id}
                for key, value in new_state.items():
                    if key in ['query_result_stats', 'query_result'] and value is not None:
                        params[key] = json.dumps(value, ensure_ascii=False, cls=DecimalEncoder)
                    else:
                        params[key] = value

                # 새로운 state row 생성
                fields = list(params.keys())
                placeholders = [f":{field}" for field in fields]
                
                insert_query = f"""
                    INSERT INTO state (
                        {', '.join(fields)}
                    ) VALUES (
                        {', '.join(placeholders)}
                    )
                """
                
                connection.execute(text(insert_query), params)

            return True

        except Exception as e:
            print(f"Error in update_state: {str(e)}")
            raise

    @staticmethod
    def get_latest_state(connection, chain_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 chain_id의 가장 최근 state 정보를 조회
        """
        query = """
            SELECT * FROM state 
            WHERE chain_id = :chain_id 
            ORDER BY id DESC 
            LIMIT 1
        """
        
        result = connection.execute(
            text(query), 
            {'chain_id': chain_id}
        ).fetchone()
        
        if result is None:
            return None

        state_dict = dict(result._mapping)

        # JSON 필드 파싱
        for key in ['query_result_stats', 'query_result']:
            if state_dict.get(key):
                try:
                    state_dict[key] = json.loads(state_dict[key])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse JSON for {key}")

        # id 필드 제거 (새로운 row 생성 시 사용하지 않음)
        state_dict.pop('id', None)
        
        return state_dict