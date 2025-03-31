import logging
import sys
import os
from typing import Optional, Dict

_loggers: Dict[str, logging.Logger] = {}


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    stdout 기반 로거 설정 (파일 핸들러 없이 logrotate-friendly)
    """
    global _loggers

    if name in _loggers:
        return _loggers[name]

    # 기존 로거 설정 완전 초기화 (루트 로거 포함)
    for logger_name in logging.root.manager.loggerDict:
        logger_obj = logging.getLogger(logger_name)
        logger_obj.handlers = []
        logger_obj.propagate = True
        logger_obj.setLevel(logging.NOTSET)

    # 루트 로거 설정 초기화
    logging.root.handlers = []

    # 새 로거 설정
    logger = logging.getLogger(name or 'default_logger')
    logger.handlers = []  # 확실하게 핸들러 제거
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - [%(process)d:%(thread)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.propagate = False
    _loggers[name] = logger
    return logger