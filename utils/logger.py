import logging
import sys
import os
from typing import Optional
from concurrent_log_handler import ConcurrentTimedRotatingFileHandler

def setup_logger(name: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """
    애플리케이션 전체에서 사용할 일관된 로거를 설정합니다.
    
    Args:
        name: 로거 이름 (기본값: None, 루트 로거 사용)
        log_file: 로그 파일 경로 (기본값: None, 로그 파일을 사용하지 않음)
        
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
    
    # 포매터 설정
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - [%(process)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 스트림 핸들러 생성 및 설정 (콘솔 출력)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # 로그 파일이 지정된 경우 파일 핸들러 추가
    if log_file:
        # 디렉토리가 없으면 생성
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # ConcurrentTimedRotatingFileHandler 설정 (멀티프로세스 안전)
        file_handler = ConcurrentTimedRotatingFileHandler(
            log_file,
            when='midnight',  # 자정에 로테이션
            interval=1,       # 1일 간격
            backupCount=30,   # 최대 30일치 보관
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        file_handler.suffix = '%Y-%m-%d'  # 로그 파일 접미사 형식
        logger.addHandler(file_handler)
    
    return logger