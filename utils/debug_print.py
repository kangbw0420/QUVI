import pandas as pd
from tabulate import tabulate  # Make sure to add tabulate to requirements.txt
from typing import Any, Dict
from time import time
from datetime import datetime

class Timer:
    _timings = {
        "nodes": {},  # 노드 전체 실행 시간
        "llm_calls": {},  # LLM 호출 시간
        "tools": {},  # 개별 tool 실행 시간
        "tool_sequences": [],  # 도구 실행 순서와 시간
    }
    _start_times = {}
    _last_tool_end = None  # 마지막 도구 종료 시간

    @classmethod
    def start_node(cls, node_name: str):
        """노드 전체 실행 시간 측정 시작"""
        cls._start_times[f"node_{node_name}"] = time()
        cls._last_tool_end = None  # 새로운 노드 시작시 초기화

    @classmethod
    def stop_node(cls, node_name: str):
        """노드 전체 실행 시간 측정 종료"""
        key = f"node_{node_name}"
        if key in cls._start_times:
            duration = time() - cls._start_times[key]
            if node_name not in cls._timings["nodes"]:
                cls._timings["nodes"][node_name] = []
            cls._timings["nodes"][node_name].append(duration)
            del cls._start_times[key]

    @classmethod
    def record_tool_execution(cls, tool_name: str, start_time: float, end_time: float):
        """도구 실행 시간과 순서 기록"""
        duration = end_time - start_time

        # 개별 도구 실행 시간 기록
        if tool_name not in cls._timings["tools"]:
            cls._timings["tools"][tool_name] = []
        cls._timings["tools"][tool_name].append(duration)

        # 도구 간 간격 계산 및 기록
        if cls._last_tool_end is not None:
            gap_duration = start_time - cls._last_tool_end
            cls._timings["tool_sequences"].append(
                {
                    "type": "gap",
                    "duration": gap_duration,
                    "start": cls._last_tool_end,
                    "end": start_time,
                }
            )

        # 도구 실행 기록
        cls._timings["tool_sequences"].append(
            {
                "type": "tool",
                "tool_name": tool_name,
                "duration": duration,
                "start": start_time,
                "end": end_time,
            }
        )

        cls._last_tool_end = end_time

    @classmethod
    def record_llm_call(cls, node_name: str, duration: float):
        """LLM 호출 시간 기록"""
        if node_name not in cls._timings["llm_calls"]:
            cls._timings["llm_calls"][node_name] = []
        cls._timings["llm_calls"][node_name].append(duration)

    @classmethod
    def print_timing_summary(cls):
        """타이밍 통계 출력"""
        # 노드별 실행 시간
        print("\nNode Execution Times:")
        headers = ["Node", "Count", "Total (s)", "Avg (s)", "Min (s)", "Max (s)"]
        for node, times in cls._timings["nodes"].items():
            print(
                f"{node}: {len(times)} executions, "
                f"total={sum(times):.3f}s, avg={sum(times)/len(times):.3f}s"
            )

        # 도구 실행 시퀀스
        print("\nTool Execution Sequence:")
        sequence_start = None
        for item in cls._timings["tool_sequences"]:
            if sequence_start is None:
                sequence_start = item["start"]

            if item["type"] == "gap":
                print(f"Gap: {item['duration']:.3f}s")
            else:
                print(f"Tool '{item['tool_name']}': {item['duration']:.3f}s")

        if sequence_start is not None and cls._timings["tool_sequences"]:
            total_sequence_time = (
                cls._timings["tool_sequences"][-1]["end"] - sequence_start
            )
            print(f"\nTotal sequence time: {total_sequence_time:.3f}s")

        # 도구별 총 실행 시간
        print("\nTotal Tool Execution Times:")
        for tool, times in cls._timings["tools"].items():
            print(
                f"{tool}: {len(times)} executions, "
                f"total={sum(times):.3f}s, avg={sum(times)/len(times):.3f}s"
            )

        # LLM 호출 시간
        print("\nLLM Call Times:")
        for node, times in cls._timings["llm_calls"].items():
            print(
                f"{node}: {len(times)} calls, "
                f"total={sum(times):.3f}s, avg={sum(times)/len(times):.3f}s"
            )

    @classmethod
    def reset(cls):
        """모든 타이밍 데이터 초기화"""
        cls._timings = {"nodes": {}, "llm_calls": {}, "tools": {}, "tool_sequences": []}
        cls._start_times = {}
        cls._last_tool_end = None


def format_value(value: Any) -> str:
    """Format different types of values for display in table"""
    if isinstance(value, pd.DataFrame):
        return f"DataFrame(shape={value.shape}, columns={list(value.columns)})"
    elif isinstance(value, dict):
        return f"Dict({len(value)} items)"
    elif isinstance(value, list):
        if not value:
            return "Empty List"
        return f"List({len(value)} items)"
    elif value is None:
        return "None"
    elif value == "":
        return "Empty String"
    else:
        return str(value)


def print_steps_table(steps: list):
    """Print steps in a table format"""
    if not steps:
        print("Steps: Empty")
        return

    headers = ["#", "Plan", "Step Name", "Tool", "Tool Input"]
    rows = []
    for i, (plan, step_name, tool, tool_input) in enumerate(steps, 1):
        rows.append([i, plan, step_name, tool, tool_input])
    print("\nSteps:")
    print(tabulate(rows, headers=headers, tablefmt="grid"))


def print_dict_table(data: Dict[str, Any], title: str):
    """Print dictionary items in a table format"""
    if not data:
        print(f"{title}: Empty")
        return

    headers = ["Key", "Value"]
    rows = [[k, format_value(v)] for k, v in data.items()]
    print(f"\n{title}:")
    print(tabulate(rows, headers=headers, tablefmt="grid"))


def print_state_debug(state: Dict[str, Any], node_name: str):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = f"\n{'='*20} {node_name} - {current_time} {'='*20}"
    print(separator)

    # 노드 이름에서 실제 노드 부분만 추출 (에러나 업데이트 상태 제외)
    base_node_name = node_name.split()[0]  # "Planner (Error)" -> "Planner"

    # 에러나 업데이트 상태가 아닌 경우에만 타이밍 측정
    if "(Error)" not in node_name and "(Updated)" not in node_name:
        Timer.start_node(base_node_name)

    # Basic Info Table
    basic_info = {
        "Task": state.get("task", "None"),
        "Plan String": state.get("plan_string", "None"),
    }
    print_dict_table(basic_info, "Basic Information")

    # Steps Table
    print_steps_table(state.get("steps", []))

    # Results Table
    print_dict_table(state.get("results", {}), "Results")

    # DataFrames Table
    dataframes = {}
    for k, v in state.get("dataframes", {}).items():
        dataframes[k] = format_value(v)
    print_dict_table(dataframes, "DataFrames")

    # Calc Data Table
    print_dict_table(state.get("calc_data", {}), "Calc Data")

    # 에러나 업데이트 상태가 아닌 경우에만 타이밍 측정 종료
    if "(Updated)" in node_name:
        Timer.stop_node(base_node_name)

    print(f"{'='*20} __{node_name} Node__ {'='*20}\n")


def print_timing_summary():
    """Print a summary of all timing information"""
    Timer.print_timing_summary()
