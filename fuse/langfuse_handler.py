from langfuse.callback import CallbackHandler
from langfuse import Langfuse
from datetime import datetime
import uuid
from typing import Dict, Any, List, Union


def create_langfuse_handler():
    try:

        class CustomCallbackHandler(CallbackHandler):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._current_span = None
                self._node_spans = {"planner": None, "executor": None, "solver": None}
                self._tool_span = None
                self._llm_span = None
                self.trace_id = str(uuid.uuid4())
                self.langfuse = Langfuse()
                self._trace = self.create_trace()

            def create_trace(self):
                return self.langfuse.trace(
                    id=self.trace_id,
                    name="AICFO Execution Trace",
                    metadata={"source": "aicfo"},
                )

            def on_chain_start(
                self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs
            ) -> None:
                if not serialized:
                    print("\nWarning: serialized is None or empty in on_chain_start")
                    return

                name = serialized.get("name", "unnamed_chain").lower()
                print(f"\nChain Start - Name: {name}")

                # 노드별로 다른 처리 (planner, executor, solver)
                if name in ["planner", "executor", "solver"]:
                    self._node_spans[name] = self._trace.span(
                        name=f"Node: {name}",
                        input=inputs,
                        metadata={
                            "node_type": name,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    self._current_span = self._node_spans[name]
                    print(f"Created span for node: {name}")

            def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
                print("\nChain End")
                active_node = None

                # 현재 활성화된 노드 찾기
                for node_name, span in self._node_spans.items():
                    if span and span == self._current_span:
                        active_node = node_name
                        break

                if active_node:
                    self._node_spans[active_node].end(
                        output=outputs,
                        metadata={
                            "end_timestamp": datetime.utcnow().isoformat(),
                            "node_status": "completed",
                            "output_summary": {
                                "type": active_node,
                                "status": "success",
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        },
                    )
                    print(f"Node span ended: {active_node}")
                    self._node_spans[active_node] = None

                self._current_span = None

            def on_llm_start(
                self, serialized: Dict[str, Any], prompts: List[str], **kwargs
            ) -> None:
                if self._current_span:
                    print("\nLLM Start")
                    self._llm_span = self._current_span.span(
                        name="LLM", input={"prompts": prompts}
                    )
                    print("Created LLM span")

            def on_llm_end(self, response: Dict[str, Any], **kwargs) -> None:
                if self._llm_span:
                    print("\nLLM End")
                    self._llm_span.end(output=response)
                    print("LLM span ended")
                    self._llm_span = None

            def on_tool_start(
                self, serialized: Dict[str, Any], input_str: str, **kwargs
            ) -> None:
                if self._current_span:
                    name = serialized.get("name", "unnamed_tool")
                    print(f"\nTool Start - Name: {name}")
                    self._tool_span = self._current_span.span(
                        name=f"Tool: {name}", input={"input": input_str}
                    )
                    print("Created tool span")

            def on_tool_end(self, output: str, **kwargs) -> None:
                if self._tool_span:
                    print("\nTool End")
                    self._tool_span.end(output={"output": output})
                    print("Tool span ended")
                    self._tool_span = None

            # retriever 관련 메소드 오버라이드 - 빈 구현
            def on_retriever_start(
                self, serialized: Dict[str, Any], query: str, **kwargs
            ) -> None:
                pass  # 아무 동작도 하지 않음

            def on_retriever_end(self, documents: List[Any], **kwargs) -> None:
                pass  # 아무 동작도 하지 않음

            # BaseCallbackHandler의 다른 retriever 관련 메소드들도 오버라이드
            def on_retriever_error(
                self,
                error: Union[Exception, KeyboardInterrupt],
                **kwargs: Any,
            ) -> None:
                pass

            def get_trace_id(self):
                return self.trace_id

        return CustomCallbackHandler()
    except Exception as e:
        print(f"Error initializing LangFuse handler: {e}")
        return None


langfuse_handler = create_langfuse_handler()
