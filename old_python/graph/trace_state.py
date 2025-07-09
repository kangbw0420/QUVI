import inspect
import functools

from langgraph.graph import StateGraph

from graph.types import GraphState
from llm_admin.state_manager import StateManager
from llm_admin.trace_manager import TraceManager

class TrackedStateGraph(StateGraph):
    """노드 실행을 추적하는 StateGraph의 확장 클래스"""
    def add_node(self, key: str, action):
        """노드 추가 시 실행 추적 래퍼를 추가"""
        async def tracked_action(state: GraphState):
            trace_id = None
            try:
                # 노드 실행 시작 시 trace 생성 및 active 상태로 기록
                trace_id = TraceManager.create_trace(state["chain_id"], key)
                
                # state에 현재 trace_id 추가(qna 기록을 위해)
                state["trace_id"] = trace_id

                # action이 코루틴 함수(async def)인지 확인
                if inspect.iscoroutinefunction(action):
                    # 비동기 함수는 await로 실행
                    result = await action(state)
                else:
                    # 동기 함수는 직접 실행
                    result = action(state)
                
                # 노드 실행 완료 시 trace completed로 변경
                if trace_id:
                    TraceManager.complete_trace(trace_id)
                
                return result
            
            except Exception as e:
                if trace_id:
                    TraceManager.mark_trace_error(trace_id)
                error_msg = str(e)
                # SQL 쿼리 에러인 경우 특별 처리
                if "psycopg" in error_msg.lower() or "invalid query" in error_msg.lower():
                    # state에 에러 정보 추가
                    state["flags"] = state.get("flags", {})
                    state["flags"]["query_error"] = True
                    state["sql_error"] = error_msg
                    return state  # 에러를 던지지 않고 state를 반환
                # 다른 예외는 그대로 던짐
                raise e
                
        return super().add_node(key, tracked_action)

def trace_state(*state_keys: str):
    """decorator managing trace_id and state_keys
    Args:
        *state_keys: StateManager에 저장할 상태 키들
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(state: GraphState, *args, **kwargs):
            # trace_id를 함수 파라미터로 사용하는지 확인
            sig = inspect.signature(func)
            needs_trace_id = 'trace_id' in sig.parameters
            
            # 함수 호출 시 trace_id 파라미터 전달
            if needs_trace_id and 'trace_id' not in kwargs:
                kwargs['trace_id'] = state['trace_id']
            
            # 함수 실행
            result = await func(state, *args, **kwargs)
            
            # 지정된 상태 키들에 대해 StateManager.update_state 호출
            if state_keys:
                update_data = {}
                for key in state_keys:
                    if key in state:
                        update_data[key] = state[key]
                
                if update_data:
                    StateManager.update_state(state['trace_id'], update_data)
            
            return result
        return wrapper
    return decorator