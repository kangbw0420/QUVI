import logging
from typing import Optional, Dict

_loggers: Dict[str, logging.Logger] = {}

def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    stdout 핸들러 없이 tee 기반 외부 로그 저장을 위한 로거 설정
    """
    global _loggers

    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name or 'default_logger')

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 로그 레벨 설정
    logger.setLevel(logging.INFO)

    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - '
        '[%(process)d:%(thread)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ✅ StreamHandler 제거 (tee가 파일에 저장하므로)
    # handler = logging.StreamHandler(sys.stdout)
    # handler.setFormatter(formatter)
    # logger.addHandler(handler)

    # propagate 비활성화
    logger.propagate = False

    _loggers[name] = logger
    return logger
