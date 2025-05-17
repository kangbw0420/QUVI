from langgraph.graph import END
from langgraph.graph.state import CompiledStateGraph

from graph.types import GraphState
from graph.trace_state import TrackedStateGraph
from graph.node import (
    checkpoint,
    isapi,
    funk,
    params,
    yqmd,
    nl2sql,
    respondent,
    executor,
    safeguard,
    nodata,
    killjoy
)

def make_graph() -> CompiledStateGraph:
    """StateGraph 생성 및 설정"""
    try:
        # TrackedStateGraph 사용
        workflow = TrackedStateGraph(GraphState)

        workflow.add_node("checkpoint", checkpoint)
        workflow.add_node("isapi", isapi)
        workflow.add_node("funk", funk) # api 함수 선택
        workflow.add_node("params", params) # api 함수 파라미터 선택
        workflow.add_node("yqmd", yqmd)
        workflow.add_node("nl2sql", nl2sql) # SQL 생성
        workflow.add_node("executor", executor) # SQL 실행 및 상태 체크
        workflow.add_node("safeguard", safeguard) # 에러 가능성 있는 쿼리를 점검
        workflow.add_node("respondent", respondent) # 답변 생성
        workflow.add_node("nodata", nodata) # 데이터가 없을 경우 답변 생성
        workflow.add_node("killjoy", killjoy) # 일상 대화 대응

        workflow.set_entry_point("checkpoint")

        workflow.add_conditional_edges(
            "checkpoint",
            lambda x: (
                "killjoy" if x["flags"]["is_joy"] else
                "isapi"
            ),
            {
                "killjoy": "killjoy",
                "isapi": "isapi"
            }
        )
        workflow.add_conditional_edges(
            "isapi",
            lambda x: (
                "funk" if x["is_api"] else
                "nl2sql"
            ),
            {
                "funk": "funk",
                "nl2sql": "nl2sql"
            }
        )
        workflow.add_edge("funk", "params")
        workflow.add_conditional_edges(
            "params",
            lambda x: (
                "END" if x["flags"]["invalid_date"] else
                "yqmd" if x["selected_api"] == "aicfo_get_financial_flow" else
                "executor"
            ),
            {
                "END": END,
                "yqmd": "yqmd",
                "executor": "executor"
            }
        )
        workflow.add_edge("yqmd", "executor")
        workflow.add_edge("nl2sql", "executor")
        
        workflow.add_conditional_edges(
            "executor",
            lambda x: (
                "END" if x["flags"]["invalid_date"] else
                # 데이터가 없었다면 데이터 없었다는 사과문 작성하러
                "nodata" if x["flags"]["no_data"] else
                # 다양한 적요 찾은 이후 그거 한 줄 답변으로 작성하기가 힘듭니다
                "END" if x["flags"]["note_changed"] else
                # 위험에 처했거나 가능성이 있는 쿼리는 safeguard로
                "safeguard" if x["flags"]["query_error"] and x["flags"].get("safe_count", 0) < 2 else
                # 그 외의 경우 respondent로
                "respondent"
            ),
            {
                "nodata": "nodata",
                "END": END,
                "safeguard": "safeguard",
                "respondent": "respondent"
            }
        )
        workflow.add_edge("safeguard", "executor")

        workflow.add_edge("respondent", END)
        workflow.add_edge("nodata", END)
        workflow.add_edge("killjoy", END)

        # 그래프 컴파일
        app = workflow.compile()
        return app
        
    except Exception as e:
        print(f"Error in make_graph: {str(e)}")
        raise