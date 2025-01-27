import json
from typing import Dict, Any, Optional
from decimal import Decimal

from database.postgresql import query_execute

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class StateManager:
    @staticmethod
    def update_state(trace_id: str, updates: Dict[str, Any]) -> bool:
        try:
            # 현재 trace의 직전 상태 조회
            current_state = StateManager.get_latest_state(trace_id)

            if current_state:
                # 현재 상태에서 updates에 있는 키를 제외한 값들만 유지
                preserved_state = {k: v for k, v in current_state.items()
                                if k not in updates.keys()
                                and v is not None
                                and k != 'trace_id'}
                # 보존된 상태에 새로운 업데이트 추가
                new_state = {**preserved_state, **updates}
            else:
                new_state = updates

            def convert_decimal(obj):
                if isinstance(obj, dict):
                    return {str(k): convert_decimal(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimal(item) for item in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                return obj

            # JSON 필드 처리
            params = {'trace_id': trace_id}
            for key, value in new_state.items():
                if key in ['query_result_stats', 'query_result'] and value is not None:
                    converted_value = convert_decimal(value)
                    params[key] = json.dumps(converted_value, ensure_ascii=False)
                else:
                    params[key] = value

            # 새로운 state row 생성
            fields = list(params.keys())
            placeholders = [f"%({field})s" for field in fields]

            insert_query = f"""
                INSERT INTO state (
                    {', '.join(fields)}
                ) VALUES (
                    {', '.join(placeholders)}
                )
            """

            return query_execute(insert_query, params, use_prompt_db=True)

        except Exception as e:
            print(f"\nError in update_state: {str(e)}")
            raise

    @staticmethod
    def get_latest_state(trace_id: str) -> Optional[Dict[str, Any]]:
        """
        현재 trace의 chain_id를 기반으로 직전 trace의 상태를 조회
        """
        query = """
            SELECT s.*
            FROM state s
            JOIN trace t ON s.trace_id = t.id
            WHERE t.chain_id = (
                SELECT chain_id 
                FROM trace 
                WHERE id = %(trace_id)s
            )
            AND t.id != %(trace_id)s
            ORDER BY t.trace_start DESC
            LIMIT 1
        """
        
        result = query_execute(query, {'trace_id': trace_id}, use_prompt_db=True)
        
        if not result or not isinstance(result, list) or len(result) == 0:
            print("No previous state found")
            return None

        state_dict = result[0]

        # JSON 필드 파싱
        for key in ['query_result_stats', 'query_result']:
            if key in state_dict and state_dict[key]:
                try:
                    state_dict[key] = json.loads(state_dict[key])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse JSON for {key}")

        # id 필드 제거 (새로운 row 생성 시 사용하지 않음)
        state_dict.pop('id', None)

        return state_dict