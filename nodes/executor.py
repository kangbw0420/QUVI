from time import time
from mock_api.api.load_cash_data import (
    load_balance_data_api,
    load_transaction_data_api,
    load_past_balance_data_api,
)
from mock_api.api.load_loan_data import (
    load_loan_balance_data_api,
    load_loan_transaction_data_api,
)
from tools.nl2sql_tools import (
    balance_handler,
    transaction_handler as trsc_handler,
    loan_balance_handler,
    loan_transaction_handler as loan_trsc_handler,
    balance_handler_past,
)
from tools.calculator_tools import calculator
from utils.types import State, _get_current_task
from utils.debug_print import print_state_debug, Timer

# tool execution node
def tool_execution(state: State):
    Timer.start_node("Tool Execution")
    print_state_debug(state, "Tool Execution")
    try:
        _step = _get_current_task(state)
        print(f"Current step: {_step}")

        if _step is None:
            print("No more steps to execute")
            Timer.stop_node("Tool Execution") 
            print("=== __Tool Execution Node__ ===\n")
            return state

        # task의 step_name, tool, tool_input 추출
        try:
            _, step_name, tool, tool_input = state["steps"][_step - 1]
            print(f"\nExecuting step: name={step_name}, tool={tool}, input={tool_input}")
        except Exception as e:
            print(f"Error unpacking step: {e}")
            print(f"Steps data: {state['steps']}")
            raise

        # results, dataframes, calc_data를 state로부터 가져옵니다.
        _results = (state["results"] or {}) if "results" in state else {}
        _dataframes = state.get("dataframes", {})
        _calc_data = state.get("calc_data", {})

        # Replace any reference to previous evidence in the tool input -> 논문에 있는 내용이지만 구현 과정에서 생략
        # for k, v in _results.items():
        #     tool_input = tool_input.replace(k, v)

        # 도구 실행
        tool_start = time()
        if tool == "load_transaction_data":
            from_date, to_date = eval(tool_input)
            # Convert YYYYMMDD to YYYY-MM-DD format
            # from_date = f"{from_date[:4]}-{from_date[4:6]}-{from_date[6:]}" if from_date else None
            # to_date = f"{to_date[:4]}-{to_date[4:6]}-{to_date[6:]}" if to_date else None
            result, df = load_transaction_data_api(from_date, to_date)

        elif tool == "load_balance_data":
            result, df, calc_data = load_balance_data_api()

        elif tool == "load_past_balance_data":
            date = eval(tool_input)
            result, df, calc_data = load_past_balance_data_api(date)

        elif tool == "transaction_sql":
            query, source = eval(tool_input)
            result, df, calc_data = trsc_handler.execute_query(query, source, _dataframes)

        elif tool == "balance_sql":
            query, source = eval(tool_input)
            result, df, calc_data = balance_handler.execute_query(
                query, source, _dataframes
            )

        elif tool == "past_balance_sql":
            query, source = eval(tool_input)
            result, df, calc_data = balance_handler_past.execute_query(
                query, source, _dataframes
            )

        elif tool == "load_loan_transaction_data":
            from_date, to_date = eval(tool_input)
            result, df = load_loan_transaction_data_api(from_date, to_date)

        elif tool == "load_loan_balance_data":
            result, df, calc_data = load_loan_balance_data_api()

        elif tool == "loan_transaction_sql":
            query, source = eval(tool_input)
            result, df, calc_data = loan_trsc_handler.execute_query(
                query, source, _dataframes
            )

        elif tool == "loan_balance_sql":
            query, source = eval(tool_input)
            result, df, calc_data = loan_balance_handler.execute_query(
                query, source, _dataframes
            )

        elif tool == "calculator":
            print(tool_input)
            result = calculator(tool_input, _calc_data)

        elif tool == "pass":
            result = ""
            pass

        else:
            raise ValueError(f"Unknown tool: {tool}")
        
        # 도구 실행 완료 시간 기록
        tool_end = time()
        if tool != "pass":  # pass는 시간 측정에서 제외
            Timer.record_tool_execution(tool, tool_start, tool_end)

        _results[step_name] = result
        if tool not in ["pass", "calculator"] and df is not None:
            _dataframes[step_name] = df
        if (
            tool
            not in [
                "pass",
                "calculator",
                "load_loan_transaction_data",
                "load_transaction_data",
            ]
            and calc_data is not None
        ):
            _calc_data[step_name] = calc_data

        updated_state = {
            "results": _results, 
            "dataframes": _dataframes, 
            "calc_data": _calc_data
        }
        print_state_debug(updated_state, "Tool Execution (Updated)")
        Timer.stop_node("Tool Execution")
        return updated_state
    
    except Exception as e:
        print(f"Error in tool_execution: {str(e)}")
        Timer.stop_node("Tool Execution") 
        return state