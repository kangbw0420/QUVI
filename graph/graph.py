from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .node import (
    GraphState,
    question_analyzer,
    query_creator,
    sql_respondent,
    result_executor,
)


def make_graph() -> CompiledStateGraph:
    workflow = StateGraph(GraphState)

    # 노드 추가
    workflow.add_node("question_analyzer", question_analyzer)
    workflow.add_node("query_creator", query_creator)
    workflow.add_node("result_executor", result_executor)
    workflow.add_node("sql_respondent", sql_respondent)

    # 엣지 추가
    workflow.add_edge("question_analyzer", "query_creator")
    workflow.add_edge("query_creator", "result_executor")
    workflow.add_edge("result_executor", "sql_respondent")
    workflow.add_edge("sql_respondent", END)

    # Entry point 설정
    workflow.set_entry_point("question_analyzer")

    # 그래프 컴파일
    app = workflow.compile()

    return app
