from langgraph.graph import END, StateGraph, START
from utils.types import State, route
from nodes.executor import tool_execution
from nodes.planner import get_plan
from nodes.solver import solve
from fuse.langfuse_handler import langfuse_handler

class LangGraphManager:
    def __init__(self):
        self.graph = None

    def initialize_graph(self):
        # 각 노드 함수에 콜백 전달을 위한 래퍼 함수들
        def plan_with_callbacks(state):
            return get_plan(state, callbacks=[langfuse_handler])
            
        def tool_with_callbacks(state):
            return tool_execution(state, callbacks=[langfuse_handler])
            
        def solve_with_callbacks(state):
            return solve(state, callbacks=[langfuse_handler])

        graph = StateGraph(State)

        # 래퍼 함수를 사용하여 노드 추가
        graph.add_node("plan", plan_with_callbacks)
        graph.add_node("tool", tool_with_callbacks)
        graph.add_node("solve", solve_with_callbacks)

        graph.add_edge(START, "plan")
        graph.add_edge("plan", "tool")
        graph.add_edge("solve", END)
        graph.add_conditional_edges("tool", route)
        
        self.graph = graph.compile()
        return self.graph