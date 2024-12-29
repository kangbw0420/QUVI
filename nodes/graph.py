from langgraph.graph import END, StateGraph, START
from utils.types import State, route
from nodes.executor import tool_execution
from nodes.planner import get_plan
from nodes.solver import solve


class LangGraphManager:
    def __init__(self):
        self.graph = None

    def initialize_graph(self):

        graph = StateGraph(State)

        graph.add_node("plan", get_plan)
        graph.add_node("tool", tool_execution)
        graph.add_node("solve", solve)

        graph.add_edge(START, "plan")
        graph.add_edge("plan", "tool")
        graph.add_edge("solve", END)
        graph.add_conditional_edges("tool", route)
        
        self.graph = graph.compile()
        return self.graph
