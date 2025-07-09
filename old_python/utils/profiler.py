import threading
import time
import os
from typing import Dict, Any, Optional
from contextvars import ContextVar

# 코루틴별 로컬 저장소 생성 (비동기 환경에서 안전)
_current_request_id: ContextVar[Optional[int]] = ContextVar('current_request_id', default=None)
_profile_data: ContextVar[Optional[Dict]] = ContextVar('profile_data', default=None)

class RequestProfiler:
    """요청 프로파일링을 위한 싱글톤 클래스"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RequestProfiler, cls).__new__(cls)
                cls._instance._init_data()
            return cls._instance
    
    def _init_data(self):
        """프로파일링 데이터 초기화"""
        # 환경변수로 프로파일링 활성화 여부 결정
        self.enabled = os.getenv('ENABLE_PROFILING', 'false').lower() == 'true'
        pass  # 전역 카운터 필요 없음
    
    def start_request(self) -> int:
        """새 요청 시작 - 요청 ID 발급"""
        if not self.enabled:
            return None
            
        # 타임스탬프 기반 고유 ID 생성
        request_id = int(time.time() * 1000000)  # 마이크로초 단위
        
        # 코루틴별 로컬에 프로파일 데이터 초기화
        _current_request_id.set(request_id)
        _profile_data.set({
            "vector_db": {"calls": 0, "total_time": 0.0},
            "llm": {"calls": 0, "total_time": 0.0},
            "db_normal": {"calls": 0, "total_time": 0.0},
            "db_prompt": {"calls": 0, "total_time": 0.0}
        })
        return request_id
    
    def get_current_request(self):
        """현재 코루틴의 요청 ID 조회"""
        if not self.enabled:
            return None
        return _current_request_id.get()
    
    def _get_profile_data(self):
        """현재 코루틴의 프로파일 데이터 조회"""
        if not self.enabled:
            return None
        return _profile_data.get()
    
    def record_vector_db_call(self, request_id: int, elapsed_time: float):
        """벡터 DB 호출 프로파일링"""
        if not self.enabled:
            return
        profile_data = self._get_profile_data()
        if profile_data:
            profile_data["vector_db"]["calls"] += 1
            profile_data["vector_db"]["total_time"] += elapsed_time
    
    def record_llm_call(self, request_id: int, elapsed_time: float):
        """LLM 호출 프로파일링"""
        if not self.enabled:
            return
        profile_data = self._get_profile_data()
        if profile_data:
            profile_data["llm"]["calls"] += 1
            profile_data["llm"]["total_time"] += elapsed_time
    
    def record_db_call(self, request_id: int, elapsed_time: float, is_prompt_db: bool = False):
        """PostgreSQL 호출 프로파일링"""
        if not self.enabled:
            return
        profile_data = self._get_profile_data()
        if profile_data:
            if is_prompt_db:
                profile_data["db_prompt"]["calls"] += 1
                profile_data["db_prompt"]["total_time"] += elapsed_time
            else:
                profile_data["db_normal"]["calls"] += 1
                profile_data["db_normal"]["total_time"] += elapsed_time
    
    def get_profile(self, request_id: int = None) -> Dict[str, Any]:
        """요청 프로파일 결과 조회"""
        if not self.enabled:
            return {}
        profile_data = self._get_profile_data()
        if not profile_data:
            return {}
            
        result = {}
        
        # 각 항목별 계산
        for key, data in profile_data.items():
            calls = data["calls"]
            total_time = data["total_time"]
            avg_time = total_time / calls if calls > 0 else 0
            
            result[key] = {
                "calls": calls,
                "total_time_ms": round(total_time * 1000, 2),
                "avg_time_ms": round(avg_time * 1000, 2)
            }
        
        return result
    
    def clear_profile(self, request_id: int = None):
        """요청 프로파일 삭제"""
        if not self.enabled:
            return
        # 코루틴별 로컬 데이터 삭제
        try:
            _current_request_id.set(None)
            _profile_data.set(None)
        except LookupError:
            pass  # 이미 삭제된 경우 무시

# 싱글톤 인스턴스 생성
profiler = RequestProfiler()