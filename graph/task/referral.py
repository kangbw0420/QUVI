from typing import List
import re

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def question_referral(
    trace_id: str, 
    user_question: str,
    selected_com: str,
    residual_com: List[str]
) -> str:
    """이것도 질문해보시겠습니까?
    Returns:
        List[str]: 각 잔여 회사에 대한 추천 질문 리스트
    """
    system_prompt = database_service.get_prompt(
        node_nm='referral', prompt_nm='system'
    )[0]['prompt'].format(selected_com=selected_com, user_question=user_question)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", user_question)
        ]
    )

    print("=" * 40 + "Referral(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    referral_chain = prompt | qwen_llm
    modified_question = referral_chain.invoke({"user_question": user_question})

    print("=" * 40 + "Referral(A)" + "=" * 40)
    print(modified_question)
    qna_manager.record_answer(qna_id, modified_question)

    # #() 패턴에서 회사명 찾기
    pattern = r'#\(([^)]+)\)'
    match = re.search(pattern, modified_question)
    
    if not match:
        return []  # 패턴이 없으면 빈 리스트 반환
        
# 각 잔여 회사에 대해 질문 생성
    referral_list = []
    template_question = modified_question
    
    for company in residual_com:
        # 먼저 #(회사명) 패턴을 잔여 회사명으로 교체
        new_question_with_sharp = re.sub(pattern, f'#({company})', template_question)
        # 그 다음 #() 패턴을 제거
        new_question = re.sub(r'#\(([^)]+)\)', r'\1', new_question_with_sharp)
        referral_list.append(new_question)

    return referral_list