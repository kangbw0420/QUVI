from time import time
import re
import uuid

from llm_models.models import closed_llm as llm
from utils.types import State
from utils.debug_print import print_state_debug, Timer
from prompts.node_prompts import get_planner_prompt
from fuse.langfuse_handler import langfuse_handler

# E#... = ...[...]를 분리해 내기 위한 Regex 패턴
regex_pattern = r"(?:Plan:\s*([^#]+))?(#E\d+)\s*=\s*(\w+)\s*\[([^\]]*)\]"


def get_plan(state: State, callbacks=None):  # callbacks 파라미터 추가
    """사용자의 task를 분석하여 실행 계획을 생성합니다."""
    Timer.start_node("Planner")
    print_state_debug(state, "Planner")
    try:
        task = state["task"]

        # dynamic shot을 통해 prompt 및 chain 생성
        prompt_template = get_planner_prompt(task)
        
        # 전달받은 callbacks 사용
        planner = prompt_template | llm.with_config(
            {
                "name": "planner",
                "callbacks": callbacks  # 함수 파라미터로 받은 callbacks 사용
            }
        )

        # LLM 호출 시간 측정
        llm_start = time()
        result = planner.invoke(
            {"task": task}
        )
        Timer.record_llm_call("Planner", time() - llm_start)
        
        print(f"\nLLM Response: {result}")

        if not result:
            print("No valid result from LLM")
            result_state = {"steps": [], "plan_string": ""}
        else:
            # 상태값에 step(E#...)과 plan_string(Plan:...)을 저장
            matches = re.findall(regex_pattern, result)
            print(f"\nRegex Matches: {matches}")
            if not matches:
                print("No plan steps found in result")
                result_state = {"steps": [], "plan_string": result}
            else:
                print(f"Found {len(matches)} plan steps")
                result_state = {"steps": matches, "plan_string": result}

        print_state_debug(result_state, "Planner (Updated)")
        Timer.stop_node("Planner")
        return result_state
    
    except Exception as e:
        print(f"\nError in get_plan: {str(e)}")
        return {"steps": [], "plan_string": ""}