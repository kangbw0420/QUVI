# from graph.task.yadon import shellder
# from graph.task.yadoran import yadoking

# async def yadon(state: GraphState) -> GraphState:
#     """last_data 기반으로 질문을 검문하는 노드"""
#     if state.get("last_data"):
#         trace_id = state["trace_id"]
#         user_question = state["user_question"]
#         last_data = state["last_data"]
#         shellder_result = await shellder(trace_id, user_question, last_data)
#         shellder_check = shellder_result == "1"
#         state["shellder"] = shellder_check
#     else:
#         state["shellder"] = False    
#     return state

# async def yadoran(state: GraphState) -> GraphState:
#     """shellder가 True일 때 질문을 재해석하는 노드"""
#     if state["shellder"]:
#         trace_id = state["trace_id"]
#         user_question = state["user_question"]
#         last_data = state["last_data"]
#         new_question = await yadoking(trace_id, user_question, last_data, today)
#         state["user_question"] = new_question
#     return state