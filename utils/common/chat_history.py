from typing import Dict, List, Tuple, Any
from utils.logger import setup_logger

logger = setup_logger("chat_history")


def convert_to_chat_history(
    history_dict: Dict[str, List[Dict[str, Any]]],
    required_fields: List[str] = ["user_question", "final_answer"],
    human_field: str = "user_question",
    ai_field: str = "final_answer",
) -> List[Tuple[str, str]]:
    """대화 히스토리 딕셔너리를 ChatPromptTemplate 형식으로 변환합니다.

    Args:
        history_dict: chain_id별로 그룹화된 과거 대화 이력
        required_fields: 필수로 포함되어야 하는 필드 목록
        human_field: 사용자 메시지에 사용할 필드명
        ai_field: AI 응답에 사용할 필드명

    Returns:
        ChatPromptTemplate 형식의 대화 히스토리 리스트
        예: [("human", "사용자 질문"), ("ai", "AI 응답"), ...]
    """
    chat_history = []

    for history_list in history_dict.values():
        for history_item in history_list:
            # 모든 필수 필드가 존재하고 None이 아닌 경우에만 추가
            if all(
                field in history_item and history_item[field] is not None
                for field in required_fields
            ):
                chat_history.append(("human", history_item[human_field]))
                chat_history.append(("ai", history_item[ai_field]))

    logger.info(f"Converted chat history: {chat_history}")
    return chat_history
