import inspect

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from llm_admin.trace_manager import TraceManager

from .node import (
    GraphState,
    yadon,
    yadoran,
    table_selector,
    api_selector,
    params_creator,
    query_creator,
    sql_respondent,
    result_executor,
    referral,
    nodata
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
        workflow.add_node("yadon", yadon)
        workflow.add_node("yadoran", yadoran)
        workflow.add_node("table_selector", table_selector)
        workflow.add_node("api_selector", api_selector)
        workflow.add_node("params_creator", params_creator)
        workflow.add_node("query_creator", query_creator)
        workflow.add_node("result_executor", result_executor)
        workflow.add_node("sql_respondent", sql_respondent)
        workflow.add_node("referral", referral)
        workflow.add_node("nodata", nodata)

        # Entry point에서 yadon으로 시작
        workflow.set_entry_point("yadon")

        # 쉘더가 야돈의 꼬리를 물면 야도란으로 진화
        workflow.add_conditional_edges(
            "yadon",
            lambda x: "END" if x["shellder"] == "no" else ("yadoran" if x["shellder"] else "table_selector"),
            {
                "yadoran": "yadoran",
                "table_selector": "table_selector",
                "END": END
            }
        )

        # yadoran은 항상 table_selector로
        workflow.add_edge("yadoran", "table_selector")

        # selector가 api를 토하면 끝남
        workflow.add_conditional_edges(
            "table_selector",
            lambda x: "api_selector" if x["selected_table"] == "api" else "query_creator",
            {
                "query_creator": "query_creator",
                "api_selector": "api_selector"
            }
        )
        workflow.add_edge("api_selector", "params_creator")
        workflow.add_edge("params_creator", "result_executor")
        
        workflow.add_edge("query_creator", "result_executor")
        
        workflow.add_conditional_edges(
            "result_executor",
            lambda x: (
                # 접근 권한이 없어서 데이터를 못 가져왔으면 종료
                "END" if x["flags"]["no_access"] else
                # 데이터가 없었다면 데이터 없었다는 사과문 작성하러
                "nodata" if x["flags"]["no_data"] else
                # 복수 회사 조회 질문을 단일 회사 조회 질문으로 바꿨다면 답변도 하고 추천 질문도 만듦
                "parallel_nodes" if x["flags"]["com_changed"] else
                # 그 외의 경우 respondent로
                "sql_respondent"
            ),
            {
                "END": END,
                "nodata": "nodata",
                "parallel_nodes": "sql_respondent", # parallel...
                "sql_respondent": "sql_respondent"
            }
        )
        workflow.add_edge("nodata", END)
        workflow.add_edge("referral", END)
        workflow.add_edge("sql_respondent", END)

        # 그래프 컴파일
        app = workflow.compile()
        return app
        
    except Exception as e:
        print(f"Error in make_graph: {str(e)}")
        raise