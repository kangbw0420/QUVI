import inspect

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from llm_admin.trace_manager import TraceManager

from .node import (
    GraphState,
    checkpoint,
    isapi,
    commander,
    funk,
    params,
    nl2sql,
    respondent,
    executor,
    safeguard,
    nodata,
    killjoy
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

def make_graph() -> CompiledStateGraph:
    """StateGraph 생성 및 설정"""
    try:
        # TrackedStateGraph 사용
        workflow = TrackedStateGraph(GraphState)

        # 노드 추가
        # workflow.add_node("yadon", yadon) # 꼬리가 물렸는지 판단
        # workflow.add_node("yadoran", yadoran) # 꼬리가 물린 후 질문을 변환
        workflow.add_node("checkpoint", checkpoint)
        workflow.add_node("isapi", isapi)
        workflow.add_node("commander", commander) # 처리 경로를 결정
        workflow.add_node("funk", funk) # api 함수 선택
        workflow.add_node("params", params) # api 함수 파라미터 선택
        workflow.add_node("nl2sql", nl2sql) # SQL 생성
        workflow.add_node("executor", executor) # SQL 실행 및 상태 체크
        workflow.add_node("safeguard", safeguard) # 에러 가능성 있는 쿼리를 점검
        workflow.add_node("respondent", respondent) # 답변 생성
        workflow.add_node("nodata", nodata) # 데이터가 없을 경우 답변 생성
        workflow.add_node("killjoy", killjoy) # 일상 대화 대응

        workflow.set_entry_point("checkpoint")
        # workflow.set_entry_point("commander")
        # workflow.set_entry_point("yadon")
        # 쉘더가 야돈의 꼬리를 물면 야도란으로 진화
        # workflow.add_conditional_edges(
        #     "yadon",
        #     lambda x: "yadoran" if x["shellder"] else "commander",
        #     {
        #         "yadoran": "yadoran",
        #         "commander": "commander"
        #     }
        # )
        # yadoran은 항상 commander로
        # workflow.add_edge("yadoran", "commander")

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
                "funk" if x["selected_table"] == "api" else
                "commander"
            ),
            {
                "funk": "funk",
                "commander": "commander"
            }
        )
        workflow.add_edge("funk", "params")
        workflow.add_edge("params", "executor")
        workflow.add_conditional_edges(
            "params",
            lambda x: (
                "END" if x["flags"]["invalid_date"] else
                "executor"
            ),
            {
                "END": END,
                "executor": "executor"
            }
        )

        workflow.add_edge("commander", "nl2sql")
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