from typing import Optional
from fastapi import WebSocket

async def send_ws_message(
    websocket: Optional[WebSocket],
    message: str,
    **kwargs
) -> None:
    """
    WebSocket 메시지를 전송하는 유틸리티 함수
    
    Args:
        websocket: WebSocket 객체 (None이면 메시지 전송 안 함)
        message: 메시지 타입 (필수)
        **kwargs: 메시지에 포함할 추가 데이터 (선택)
    
    Example:
        await send_ws_message(websocket, "nl2sql_start")
        await send_ws_message(websocket, "nl2sql_end", sql_query=query)
        await send_ws_message(websocket, "respondent_start", 
                            result_column=len(columns), 
                            result_row=len(df))
    """
    if websocket is None:
        return
        
    data = {
        "status": "success",
        "message": message,
        **kwargs
    }
    
    await websocket.send_json(data) 