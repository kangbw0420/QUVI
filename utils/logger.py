import logging
import sys
import os
import fcntl
from typing import Optional, Dict
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
        filename=log_file,
        when='midnight',  # 자정에 로테이션
        interval=1,  # 1일 간격
        backupCount=30,  # 최대 30일치 보관
        encoding='utf-8',
        delay=False,  # 즉시 파일 생성
        utc=False,  # 로컬 시간 사용
        use_gzip=False,  # gzip 압축 사용 안함
    )

    # 로그 파일 접미사 형식 설정: YYYY-MM-DD
    file_handler.suffix = "%Y-%m-%d"

    # lock_file 속성 설정 - 이 부분이 중요합니다!
    # 이를 통해 모든 프로세스가 동일한 락 파일을 사용하게 됩니다
    lock_file = f"{log_file}.lock"
    setattr(file_handler, 'lockFilename', lock_file)

    # 커스텀 namer 함수 정의
    def namer(name):
        base_name = os.path.basename(log_file)
        dir_name = os.path.dirname(log_file)
        date_str = file_handler.suffix

        # agent.log -> agent.log.2025-03-22
        return os.path.join(dir_name, f"{base_name}.{date_str}")

    file_handler.namer = namer

    # 커스텀 rotator 함수
    def rotator(source, dest):
        # 락 파일 생성하여 다른 프로세스의 접근 제어
        lock_file_path = f"{source}.rotate.lock"
        with open(lock_file_path, 'w') as lock_file:
            try:
                # 파일 락 획득
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

                # 이미 대상 파일이 존재하면 내용 병합
                if os.path.exists(dest):
                    with open(source, 'rb') as sf:
                        with open(dest, 'ab') as df:
                            df.write(sf.read())
                    os.remove(source)
                else:
                    # 파일 이름 변경
                    os.rename(source, dest)
            finally:
                # 락 해제
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

        # 락 파일 삭제
        try:
            os.remove(lock_file_path)
        except OSError:
            pass

    file_handler.rotator = rotator

    # 로그 파일 패턴 설정을 간단하게 유지
    file_handler.extMatch = False

    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 다른 모듈로 로그가 전파되지 않도록 설정
    logger.propagate = False

    # 싱글톤 패턴으로 로거 저장
    _loggers[name] = logger

    return logger