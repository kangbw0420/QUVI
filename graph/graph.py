from click import option
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from functools import partial
from llm_admin.trace_manager import TraceManager

from .node import (
    GraphState,
    table_selector,
    question_analyzer,
    query_creator,
    sql_respondent,
    result_executor,
)

trace_manager = TraceManager()

async def wrap_node_with_trace(node_func, node_name: str, state: GraphState):
    """
    노드 함수를 trace 기록 로직으로 감싸는 래퍼 함수
    """
    try:
        # 노드 실행
        result_state = await node_func(state)
        
        # Trace 기록 (성공)
        if 'chain_id' in state:
            trace_manager.create_trace(
                chain_id=state['chain_id'],
                node_type=node_name,
                status='completed'
            )
        
        return result_state
        
    except Exception as e:
        # Trace 기록 (실패)
        if 'chain_id' in state:
            trace_id = trace_manager.create_trace(
                chain_id=state['chain_id'],
                node_type=node_name,
                status='error'
            )
        raise e

def make_graph() -> CompiledStateGraph:
    try:
        workflow = StateGraph(GraphState)

        # 노드 추가 (trace 래퍼 적용)
        workflow.add_node("table_selector", 
            partial(wrap_node_with_trace, table_selector, "table_selector"))
        workflow.add_node("question_analyzer", 
            partial(wrap_node_with_trace, question_analyzer, "question_analyzer"))
        workflow.add_node("query_creator", 
            partial(wrap_node_with_trace, query_creator, "query_creator"))
        workflow.add_node("result_executor", 
            partial(wrap_node_with_trace, result_executor, "result_executor"))
        workflow.add_node("sql_respondent", 
            partial(wrap_node_with_trace, sql_respondent, "sql_respondent"))

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