import logging
import sys
from typing import Optional

def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    애플리케이션 전체에서 사용할 일관된 로거를 설정합니다.
    
    Args:
        name: 로거 이름 (기본값: None, 루트 로거 사용)
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    # 로거 가져오기
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있다면 추가 설정하지 않음
    if logger.handlers:
        return logger
        
    # 로그 레벨 설정
    logger.setLevel(logging.INFO)
    
    # 스트림 핸들러 생성 및 설정
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # 포매터 설정
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - [%(process)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(handler)
    
    return logger