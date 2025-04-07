import json
from typing import List

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.postgresql import get_prompt
from graph.models import qwen_llm
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger('commander')

async def command(trace_id: str, user_question: str) -> List[str]:
    output_parser = StrOutputParser()

    system_prompt = get_prompt(node_nm='commander', prompt_nm='join')[0]['prompt']

    few_shots = await retriever.get_few_shots(
        query_text=user_question,
        collection_name="commander_join",
        top_k=5
    )
    few_shot_prompt = []
    for example in reversed(few_shots):
        few_shot_prompt.append(("human", example["input"]))
        if "stats" in example:
            ouput_with_reason = f'{{"table": "{example["output"]}", "reason": "{example["stats"]}"}}'
            few_shot_prompt.append(("ai", ouput_with_reason))
        else:
            few_shot_prompt.append(("ai", example["output"]))

    COMMANDER_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            ("human", user_question)
        ]
    )

    logger.debug("===== commander_join(Q) =====")
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=COMMANDER_PROMPT,
        model="qwen_llm"
    )

    commander_chain = COMMANDER_PROMPT | qwen_llm | output_parser
    response_json = commander_chain.invoke({"user_question": user_question})
    logger.debug("===== commander_join(A) =====")
    logger.info("response_json")
    qna_manager.record_answer(qna_id, str(response_json))
    
    # JSON 응답에서 'table' 키의 값 추출
    try:
        if isinstance(response_json, str):
            response_dict = json.loads(response_json)
        else:
            # 이미 딕셔너리로 파싱된 경우
            response_dict = response_json
            
        table_value = response_dict.get("table", "")
        
        # table 값을 처리: 문자열이면 쉼표로 분할, 아니면 리스트로 변환
        if isinstance(table_value, str):
            # 쉼표로 구분된 테이블 이름을 분할하고 공백 제거
            selected_tables = [table.strip() for table in table_value.split(',') if table.strip()]
        elif isinstance(table_value, list):
            # 이미 리스트인 경우 그대로 사용
            selected_tables = table_value
        else:
            # 다른 유형의 경우 문자열로 변환 후 리스트에 추가
            selected_tables = [str(table_value)]
            
        # 빈 리스트인 경우 처리
        if not selected_tables:
            selected_tables = [""]
            
    except Exception as e:
        logger.error(f"Error parsing JSON response: {str(e)}")
        # 파싱 실패 시 전체 응답을 문자열로 간주하고 리스트에 담기
        selected_tables = [str(response_json)]
    
    return selected_tables