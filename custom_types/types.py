from typing import TypedDict, List, Dict, Optional
import pandas as pd
from pydantic import BaseModel
from custom_types.chart_types import ChartData


# 단계별로 처리될 때 그 결과를 어떻게 보고할 것인가
class Step(TypedDict):
    plan: str
    step_name: str
    tool: str
    tool_input: str


# agent가 유지할 state를 정의
# planner는 입력으로 task만 필요, 출력으로 steps와 plan_string만 생성. 근데 어차피 null로 두면 되고 타입 바꾸기 귀찮으니 이대로
class State(TypedDict):
    task: str
    plan_string: str
    steps: List
    results: dict
    result: str
    dataframes: Dict[str, pd.DataFrame]
    calc_data: dict


class AnalysisResponse(BaseModel):
    answer: str  # 필수: 항상 있어야 하는 요약 답변
    chartType: Optional[str]  # 선택: 시각화가 필요한 경우만 ("bar", "line", "pie" 등)
    """프론트 보고 이거 배열로 수정하셈. 0개면 하나그리기, 1개면 하나 더 밑에 그리기"""
    chart: Optional[ChartData]  # 선택: chartType이 있는 경우에만 존재


def _get_current_task(state: State):
    if "results" not in state or state["results"] is None:
        return 1
    if len(state["results"]) == len(state["steps"]):
        return None
    else:
        return len(state["results"]) + 1


def route(state):
    print(f"\n=== Route Decision ===")
    print(f"Current state results count: {len(state.get('results', {}))}")
    print(f"Total steps planned: {len(state.get('steps', []))}")

    _step = _get_current_task(state)
    
    # route 함수 내부에서만 사용하는 static 변수로 재시도 횟수 관리
    if not hasattr(route, 'retry_count'):
        route.retry_count = 0
    if not hasattr(route, 'last_step'):
        route.last_step = None

    # 같은 스텝이 반복되면 재시도로 간주
    if _step == route.last_step:
        route.retry_count += 1
        print(f"Retry count for step {_step}: {route.retry_count}")
        
        # 최대 재시도 횟수(3회) 초과시 다음 단계로 강제 진행
        if route.retry_count >= 3:
            print(f"Maximum retries exceeded for step {_step}, forcing next step")
            route.retry_count = 0  # 재시도 카운트 리셋
            # 마지막 스텝이면 solve로, 아니면 다음 스텝으로
            return "solve" if _step >= len(state['steps']) else "tool"
    else:
        # 다른 스텝으로 넘어가면 재시도 카운트 리셋
        route.retry_count = 0
        route.last_step = _step

    result = "solve" if _step is None else "tool"
    print(f"Next step: {_step}")
    print(f"Routing to: {result}")
    print("=== Route Decision End ===\n")

    return result
