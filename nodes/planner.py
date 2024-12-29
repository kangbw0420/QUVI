from time import time
from llm_models.models import closed_llm as llm
import re
from utils.types import State
from prompts.node_prompts import get_planner_prompt
from utils.debug_print import print_state_debug, Timer

# E#... = ...[...]를 분리해 내기 위한 Regex 패턴
regex_pattern = r"(?:Plan:\s*([^#]+))?(#E\d+)\s*=\s*(\w+)\s*\[([^\]]*)\]"

def get_plan(state: State):
    """사용자의 task를 분석하여 실행 계획을 생성합니다."""
    Timer.start_node("Planner")
    print_state_debug(state, "Planner")
    try:  
        task = state["task"]

        # dynamic shot을 통해 prompt 및 chain 생성
        prompt_template = get_planner_prompt(task)
        # 위의 prompt_template과 llm 체이닝
        planner = prompt_template | llm

        # LLM 호출 시간 측정
        llm_start = time()
        result = planner.invoke({"task": task})
        Timer.record_llm_call("Planner", time() - llm_start)
        
        print(f"LLM Response: {result}")

        if not result or not result:
            return {"steps": [], "plan_string": ""}
        
        # 상태값에 step(E#...)과 plan_string(Plan:...)을 저장
        matches = re.findall(regex_pattern, result)
        print(f"Regex Matches: {matches}")
        if not matches:
            return {"steps": [], "plan_string": result}
            
        result_state = {"steps": matches, "plan_string": result}
        print_state_debug(result_state, "Planner (Updated)")
        Timer.stop_node("Planner")
        return result_state
#         return result_state
    
    except Exception as e:
        print(f"Error in get_plan: {str(e)}")
        return {"steps": [], "plan_string": ""}