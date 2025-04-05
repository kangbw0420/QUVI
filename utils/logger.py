import logging
import sys
import os
from typing import Optional, Dict
import time
from concurrent_log_handler import ConcurrentTimedRotatingFileHandler

# 싱글톤 패턴으로 로거 인스턴스 관리
_loggers: Dict[str, logging.Logger] = {}


def setup_logger(name: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """
    애플리케이션 전체에서 사용할 일관된 로거를 설정합니다.

    Args:
        name: 로거 이름 (기본값: None, 루트 로거 사용)
        log_file: 로그 파일 경로 (기본값: None, 로그 파일을 사용하지 않음)

    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    global _loggers

    # 이미 설정된 로거가 있다면 재사용
    if name in _loggers:
        return _loggers[name]

    # 로그 디렉토리 설정
    if not log_file:
        log_dir = os.environ.get('LOG_DIR', 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, 'agent.log')

    # 로거 가져오기
    logger = logging.getLogger(name or 'root')

    # 이미 핸들러가 설정되어 있다면 모두 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 로그 레벨 설정 - DEBUG로 변경하여 더 자세한 로그 출력
    logger.setLevel(logging.DEBUG)

    # 포매터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - [%(process)d:%(thread)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 스트림 핸들러 생성 및 설정 (콘솔 출력)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)  # 콘솔에는 INFO 레벨 이상만 출력
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 로그 파일 핸들러 추가
    # 디렉토리가 없으면 생성
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # ConcurrentTimedRotatingFileHandler 설정 (멀티프로세스 안전)
    file_handler = ConcurrentTimedRotatingFileHandler(
        filename=log_file,
        mode='a',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8',
        delay=False,
        utc=False
    )

    # 파일에는 DEBUG 레벨까지 모든 로그 출력
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 다른 모듈로 로그가 전파되지 않도록 설정
    logger.propagate = False

    # 로거 설정 완료 로그
    logger.info(f"Logger '{name}' initialized with log file: {log_file}")

    # 싱글톤 패턴으로 로거 저장
    _loggers[name] = logger

    return logger