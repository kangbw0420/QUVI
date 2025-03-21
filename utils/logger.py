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
        log_file = os.path.join(log_dir, 'agent.log')  # 'server.log' 대신 사용

    # 로거 가져오기
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있다면 모두 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 로그 레벨 설정
    logger.setLevel(logging.INFO)

    # 포매터 설정
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - [%(process)d:%(thread)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 스트림 핸들러 생성 및 설정 (콘솔 출력)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 로그 파일 핸들러 추가
    # 디렉토리가 없으면 생성
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # ConcurrentTimedRotatingFileHandler 설정 (멀티프로세스 안전)
    file_handler = ConcurrentTimedRotatingFileHandler(
        log_file,
        when='midnight',  # 자정에 로테이션
        interval=1,  # 1일 간격
        backupCount=30,  # 최대 30일치 보관
        encoding='utf-8',
        delay=False,  # 즉시 파일 생성
        utc=False  # 로컬 시간 사용
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    # 로그 파일 접미사 형식을 정확하게 설정
    file_handler.suffix = '%Y-%m-%d'
    # 로테이션 파일 이름 패턴 커스터마이징
    file_handler.namer = lambda name: name.replace(".log", "") + ".log"
    # extMatch를 False로 설정하여 새 로그 파일이 시작될 때 기존 로그 파일을 모두 검사
    file_handler.extMatch = False
    logger.addHandler(file_handler)

    # 다른 모듈로 로그가 전파되지 않도록 설정
    logger.propagate = False

    # 싱글톤 패턴으로 로거 저장
    _loggers[name] = logger

    return logger