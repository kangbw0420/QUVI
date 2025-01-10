from click import option
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from llm_admin.trace_manager import TraceManager
import inspect

from .node import (
    GraphState,
    table_selector,
    question_analyzer,
    query_creator,
    sql_respondent,
    result_executor,
)

class TrackedStateGraph(StateGraph):
    """노드 실행을 추적하는 StateGraph의 확장 클래스"""
    
    def add_node(self, key: str, action):
        """노드 추가 시 실행 추적 래퍼를 추가"""
        async def tracked_action(state: GraphState):
            trace_id = None
            try:
                # 노드 실행 시작 시 trace 생성 및 active 상태로 기록
                trace_id = TraceManager.create_trace(state["chain_id"], key)
                
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
                # 에러 발생 시 trace를 error로 마크
                if trace_id:
                    TraceManager.mark_trace_error(trace_id)
                raise e
                
        return super().add_node(key, tracked_action)

def make_graph() -> CompiledStateGraph:
    """StateGraph 생성 및 설정"""
    try:
        # TrackedStateGraph 사용
        workflow = TrackedStateGraph(GraphState)

        # 노드 추가
        workflow.add_node("table_selector", table_selector)
        workflow.add_node("question_analyzer", question_analyzer)
        workflow.add_node("query_creator", query_creator)
        workflow.add_node("result_executor", result_executor)
        workflow.add_node("sql_respondent", sql_respondent)

        # 엣지 추가
        workflow.add_edge("table_selector", "question_analyzer")
        workflow.add_edge("question_analyzer", "query_creator")
        workflow.add_edge("query_creator", "result_executor")
        workflow.add_edge("result_executor", "sql_respondent")
        workflow.add_edge("sql_respondent", END)

        # Entry point 설정
        workflow.set_entry_point("table_selector")

        # 그래프 컴파일
        app = workflow.compile()
        return app
        
    except Exception as e:
        print(f"Error in make_graph: {str(e)}")
        raise