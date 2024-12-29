from langfuse.callback import CallbackHandler
from langfuse import Langfuse
from dotenv import load_dotenv
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List

load_dotenv()

def create_langfuse_handler():
    try:
        class CustomCallbackHandler(CallbackHandler):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._current_span = None
                self._tool_span = None
                self._llm_span = None
                self.trace_id = str(uuid.uuid4())
                self.langfuse = Langfuse()
                self._trace = self.create_trace()
            
            def create_trace(self):
                return self.langfuse.trace(
                    id=self.trace_id,
                    name="LangChain Trace",
                    metadata={"source": "langchain"}
                )

            def on_chain_start(
                self,
                serialized: Optional[Dict[str, Any]] = None,
                inputs: Optional[Dict[str, Any]] = None,
                **kwargs
            ) -> None:
                name = kwargs.get('name', 'unnamed_chain')
                if serialized:
                    name = serialized.get('name', name)
                
                self._current_span = self._trace.span(
                    name=f"Node: {name}",
                    input=inputs or {},
                    start_time=datetime.utcnow()
                )

            def on_chain_end(
                self,
                outputs: Optional[Dict[str, Any]] = None,
                **kwargs
            ) -> None:
                if self._current_span:
                    self._current_span.end(
                        output=outputs or {},
                        end_time=datetime.utcnow()
                    )
                    self._current_span = None

            def on_tool_start(
                self,
                serialized: Optional[Dict[str, Any]] = None,
                input_str: Optional[str] = None,
                **kwargs
            ) -> None:
                if self._current_span:
                    name = kwargs.get('name', 'unnamed_tool')
                    if serialized:
                        name = serialized.get('name', name)
                    
                    self._tool_span = self._current_span.span(
                        name=f"Tool: {name}",
                        input={"input": input_str} if input_str else {},
                        start_time=datetime.utcnow()
                    )

            def on_tool_end(
                self,
                output: Optional[str] = None,
                **kwargs
            ) -> None:
                if self._tool_span:
                    self._tool_span.end(
                        output={"output": output} if output else {},
                        end_time=datetime.utcnow()
                    )

            def on_llm_start(
                self,
                serialized: Optional[Dict[str, Any]] = None,
                prompts: Optional[List[str]] = None,
                **kwargs
            ) -> None:
                if self._current_span:
                    name = kwargs.get('name', 'unnamed_llm')
                    if serialized:
                        name = serialized.get('name', name)
                    
                    self._llm_span = self._current_span.span(
                        name=f"LLM: {name}",
                        input={"prompts": prompts} if prompts else {},
                        start_time=datetime.utcnow()
                    )

            def on_llm_end(
                self,
                response: Optional[Dict[str, Any]] = None,
                **kwargs
            ) -> None:
                if self._llm_span:
                    self._llm_span.end(
                        output=response or {},
                        end_time=datetime.utcnow()
                    )

            def on_retriever_start(
                self,
                serialized: Optional[Dict[str, Any]] = None,
                query: Optional[str] = None,
                **kwargs
            ) -> None:
                name = kwargs.get('name', 'unnamed_retriever')
                if serialized:
                    name = serialized.get('name', name)
                
                # Create a new span for retriever
                self._retriever_span = self._trace.span(
                    name=f"Retriever: {name}",
                    input={"query": query} if query else {},
                    start_time=datetime.utcnow()
                )

            def on_retriever_end(
                self,
                documents: Optional[List[Any]] = None,
                **kwargs
            ) -> None:
                if hasattr(self, '_retriever_span') and self._retriever_span:
                    self._retriever_span.end(
                        output={"documents": str(documents)} if documents else {},
                        end_time=datetime.utcnow()
                    )
                    self._retriever_span = None

        return CustomCallbackHandler()
    except Exception as e:
        print(f"Error initializing LangFuse handler: {e}")
        return None

langfuse_handler = create_langfuse_handler()