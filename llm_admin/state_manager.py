import json
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal

from core.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger('state_manager')

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class StateManager:
    @staticmethod
    def update_state(trace_id: str, updates: Dict[str, Any]) -> bool:
        """state 테이블에 새로운 상태 추가. 이전 상태에서 updates에 없는 값들은 보존하고 Decimal은 float로 변환
        Args:
            updates: 갱신할 상태값들의 dictionary. query_result_stats와 query_result는 JSON으로 저장
        Returns:
            state 저장 성공 여부
        """
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
                elif isinstance(obj, tuple):
                    return list(convert_decimal(item) for item in obj)
                return obj

            # JSON 필드 처리
            params = {'trace_id': trace_id}
            for key, value in new_state.items():
                if key in ['query_result', 'column_list'] and value is not None:
                    converted_value = convert_decimal(value)
                    params[key] = json.dumps(converted_value, ensure_ascii=False)
                elif key == 'date_info' and value is not None:
                    # date_info는 tuple이므로 리스트로 변환하여 저장
                    if isinstance(value, tuple) and len(value) == 2:
                        params[key] = json.dumps(list(value), ensure_ascii=False)
                    else:
                        params[key] = None
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
            logger.error(f"Error in update_state: {str(e)}")
            raise

    @staticmethod
    def get_latest_state(trace_id: str) -> Optional[Dict[str, Any]]:
        """현재 trace와 같은 chain_id를 가진 직전 trace의 state를 조회. JSON 필드는 파싱하여 반환
        Returns:
            이전 상태 dictionary 또는 None (이전 state가 없는 경우)
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
            logger.info("No previous state found")
            return None

        state_dict = result[0]

        # JSON 필드 파싱
        for key in ['query_result', 'column_list']:
            if key in state_dict and state_dict[key]:
                try:
                    # 문자열이면 JSON으로 파싱, 아니면 그대로 사용
                    if isinstance(state_dict[key], str):
                        state_dict[key] = json.loads(state_dict[key])
                except json.JSONDecodeError:
                    logger.error(f"Warning: Could not parse JSON for {key}")
        
        # date_info JSON을 tuple로 변환
        if 'date_info' in state_dict and state_dict['date_info']:
            try:
                # 타입 체크 - 문자열인 경우에만 json.loads 적용
                if isinstance(state_dict['date_info'], str):
                    date_info_list = json.loads(state_dict['date_info'])
                    if isinstance(date_info_list, list) and len(date_info_list) == 2:
                        state_dict['date_info'] = tuple(date_info_list)
                    else:
                        state_dict['date_info'] = (None, None)
                elif isinstance(state_dict['date_info'], list) and len(state_dict['date_info']) == 2:
                    # 이미 리스트로 파싱되어 있는 경우
                    state_dict['date_info'] = tuple(state_dict['date_info'])
                else:
                    state_dict['date_info'] = (None, None)
            except json.JSONDecodeError:
                logger.error("Warning: Could not parse JSON for date_info")
                state_dict['date_info'] = (None, None)
            except Exception as e:
                logger.error(f"Error processing date_info: {str(e)}")
                state_dict['date_info'] = (None, None)

        # id 필드 제거 (새로운 row 생성 시 사용하지 않음)
        state_dict.pop('id', None)

        return state_dict