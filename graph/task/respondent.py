from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm, solver
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def response(trace_id: str, user_question, query_result_stats = None, query_result = None) -> str:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다.
    Returns:
        str: 생성된 자연어 응답.
    Raises:
        ValueError: 프롬프트 템플릿 로딩 실패 또는 LLM 응답 생성 실패시.
    """
    output_parser = StrOutputParser()

    system_prompt = database_service.get_prompt(node_nm='respondent', prompt_nm='system')[0]['prompt']

    few_shots = await retriever.get_few_shots(
        query_text=user_question,
        collection_name="shots_respondent",
        top_k=3
    )
    few_shot_prompt = []
    for example in few_shots:
        if "stats" in example:
            human_with_stats = f'참고할 데이터:\n{example["stats"]}\n\n사용자의 질문:\n{example["input"]}'
        else:
            human_with_stats = example["input"]
        few_shot_prompt.append(("human", human_with_stats))
        few_shot_prompt.append(("ai", example["output"]))


    # 통곗값이 있으면 통곗값을 쓰고, 아니면 결과 자체를 사용
    human_prompt = database_service.get_prompt(node_nm='respondent', prompt_nm='human')[0]['prompt'].format(
        query_result_stats=query_result_stats if query_result_stats is not None else query_result, user_question=user_question
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            ("human", human_prompt),
        ]
    )

    print("=" * 40 + "respondent(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    chain = prompt | solver | output_parser
    output = chain.invoke({"human_prompt": user_question})

    print("=" * 40 + "respondent(A)" + "=" * 40)
    print(output)
    qna_manager.record_answer(qna_id, output)

    return output
