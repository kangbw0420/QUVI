from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import isapi
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def is_api(trace_id: str, user_question: str) -> bool:
    """사용자의 질문을 api로 처리할 수 있는지 확인
    Returns:
        str: 0 or 1
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    system_prompt = database_service.get_prompt(node_nm='isapi', prompt_nm='system')[0]['prompt']

    # few_shots = await retriever.get_few_shots(
    #     query_text=user_question, collection_name="shots_selector", top_k=5
    # )
    # few_shot_prompt = []
    # for example in reversed(few_shots):
    #     few_shot_prompt.append(("human", example["input"]))
    #     few_shot_prompt.append(("ai", example["output"]))

    ISAPI_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            # *few_shot_prompt,
            ("human", user_question)
        ]
    )

    print("=" * 40 + "isapi(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=ISAPI_PROMPT,
        model="qwen_selector"
    )

    isapi_chain = ISAPI_PROMPT | isapi | output_parser
    selected_table = isapi_chain.invoke({"user_question": user_question})

    print("=" * 40 + "isapi(A)" + "=" * 40)
    print(selected_table)
    qna_manager.record_answer(qna_id, selected_table)

    return selected_table