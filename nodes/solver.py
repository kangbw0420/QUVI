from time import time
import json
from utils.types import State
from llm_models.models import solver_llm as llm
from utils.debug_print import print_state_debug, Timer
from database.postgresql import get_prompt
from fuse.langfuse_handler import langfuse_handler

json_schema_part = get_prompt("solver_json_schema_part")[0]['prompt']
explanation_part = get_prompt("solver_explanation_part")[0]['prompt']
example_part = get_prompt("solver_example_part")[0]['prompt']

solve_prompt = json_schema_part + explanation_part + example_part
print(solve_prompt)

def solve(state: State):
    Timer.start_node("Solver")
    print_state_debug(state, "Solver")
    try:
        # Langfuse에 solver 노드 시작을 기록
        if langfuse_handler:
            langfuse_handler.on_chain_start(
                serialized={"name": "solver"},  # 명시적으로 이름 지정
                inputs=state
            )

        # Build the plan string
        plan = ""
        for _plan, step_name, tool, tool_input in state["steps"]:
            _results = (state["results"] or {}) if "results" in state else {}
            print(f"Available results for replacement: {_results}")
            for k, v in _results.items():
                if not tool == "calculator":
                    tool_input = tool_input.replace(k, v)
                step_name = step_name.replace(k, v)
            plan += f"{_plan}{step_name}\n"
        
        print(f"\nFinal plan string: {plan}")

        # Get the last dataframe and its columns if available
        print("\n=== Extracting DataFrame Columns ===")
        dataframes = state.get("dataframes", {})
        columns = []
        if dataframes:
            print(f"Available dataframe keys: {list(dataframes.keys())}")
            last_key = max(dataframes.keys())  # #E1, #E2 등 중 마지막 키
            print(f"Selected last key: {last_key}")
            last_df = dataframes[last_key]
            if last_df is not None and hasattr(last_df, 'columns'):
                columns = list(last_df.columns)
                print(f"Extracted columns: {columns}")
            else:
                print("Warning: Last dataframe is None or has no columns attribute")
        else:
            print("Warning: No dataframes available in state")

        print("\n=== Building Prompt ===")
        print(f"Task: {state['task']}")
        print(f"Plan: {plan}")
        print(f"Columns: {columns}")

        try:
            # Combine prompt parts and format with task, plan and columns
            formatted_explanation = explanation_part.format(
                task=state["task"],
                plan=plan,
                columns=columns
            )
            # Combine all parts (json_schema_part doesn't need formatting)
            prompt = "\n".join([json_schema_part, formatted_explanation, example_part])
            print("\n=== Successfully Built Prompt ===")
        except Exception as e:
            print(f"\n=== Error Building Prompt ===")
            print(f"Error details: {str(e)}")
            raise

        # LLM 호출 시간 측정
        llm_start = time()
        try:
            result = llm.invoke(prompt)
            print("\nRaw LLM result object:")
            print(f"Type: {type(result)}")
            print(f"Result: {result}")
        except Exception as e:
            print(f"\nError during LLM invocation: {str(e)}")
            raise
        Timer.record_llm_call("Solver", time() - llm_start)

        print("\nLLM Response:")
        print(result)

        if not result:
            result_state = {
                "task": state.get("task", ""),
                "plan_string": state.get("plan_string", ""),
                "steps": state.get("steps", []),
                "results": state.get("results", {}),
                "dataframes": state.get("dataframes", {}),
                "calc_data": state.get("calc_data", {}),
                "result": {
                    "answer": "죄송합니다. 응답을 생성하는 데 문제가 발생했습니다.",
                    "table": {"columns": []},
                },
            }
            print_state_debug(result_state, "Solver (Error Response)")
            return result_state

        try:
            print("\n=== Processing LLM Response ===")
            # Parse JSON response
            content = result.strip()
            print(f"Stripped content: {content}")
            response_dict = json.loads(content)
            print(f"Parsed JSON: {json.dumps(response_dict, indent=2, ensure_ascii=False)}")
            
            # Extract answer and table info
            answer = response_dict.get("answer", "응답 형식이 올바르지 않습니다.")
            table_info = response_dict.get("table", {"columns": []})
            print(f"Extracted answer: {answer}")
            print(f"Extracted table info: {table_info}")
            
            result_state = {
                "task": state.get("task", ""),
                "plan_string": state.get("plan_string", ""),
                "steps": state.get("steps", []),
                "results": state.get("results", {}),
                "dataframes": state.get("dataframes", {}),
                "calc_data": state.get("calc_data", {}),
                "result": {
                    "answer": answer,
                    "table": table_info
                },
            }
            
        except json.JSONDecodeError as e:
            print(f"\n=== JSON Parsing Error ===")
            print(f"Error details: {str(e)}")
            print(f"Falling back to plain text response")
            # Fallback for non-JSON responses
            result_state = {
                "task": state.get("task", ""),
                "plan_string": state.get("plan_string", ""),
                "steps": state.get("steps", []),
                "results": state.get("results", {}),
                "dataframes": state.get("dataframes", {}),
                "calc_data": state.get("calc_data", {}),
                "result": {
                    "answer": content,
                    "table": {"columns": columns if columns else []}
                },
            }

        print_state_debug(result_state, "Solver (Updated)")
        Timer.stop_node("Solver")
        return result_state

    except Exception as e:
        print(f"Error in solve: {str(e)}")
        error_state = {
            "task": state.get("task", ""),
            "plan_string": state.get("plan_string", ""),
            "steps": state.get("steps", []),
            "results": state.get("results", {}),
            "dataframes": state.get("dataframes", {}),
            "calc_data": state.get("calc_data", {}),
            "result": {
                "answer": f"처리 중 오류가 발생했습니다: {str(e)}", 
                "table": {"columns": []}
            },
        }
        print_state_debug(error_state, "Solver (Error State)")
        return error_state