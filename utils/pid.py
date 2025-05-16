import os
import json
import time
import sys
from utils.logger import setup_logger

logger = setup_logger("pid_manager")

class PIDManager:
    def __init__(self, app_name="app"):
        self.app_name = app_name
        self.pid_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"{app_name}.pids.json")
    
    def write_pid(self):
        """PID 정보를 JSON 파일에 추가"""
        pid_info = {
            "pid": os.getpid(),
            "worker_id": os.environ.get('WORKER_ID', '0'),
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "command": " ".join(sys.argv),
            "user": os.getenv("USER", "unknown")
        }
        
        # 기존 PID 정보 읽기
        existing_pids = {}
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    existing_pids = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid PID file, creating new one")
        
        # 새로운 PID 정보 추가
        existing_pids[str(pid_info['pid'])] = pid_info
        
        # PID 정보 저장
        with open(self.pid_file, 'w') as f:
            json.dump(existing_pids, f, indent=2)
        
        logger.info(f"PID file updated for worker {pid_info['worker_id']}: {self.pid_file}")
    
    def remove_pid(self):
        """현재 프로세스의 PID 정보를 JSON 파일에서 제거"""
        if not os.path.exists(self.pid_file):
            return
            
        try:
            with open(self.pid_file, 'r') as f:
                pids = json.load(f)
            
            # 현재 프로세스의 PID 제거
            if str(os.getpid()) in pids:
                del pids[str(os.getpid())]
                
                # PID 정보가 남아있으면 파일 업데이트, 없으면 파일 삭제
                if pids:
                    with open(self.pid_file, 'w') as f:
                        json.dump(pids, f, indent=2)
                else:
                    os.remove(self.pid_file)
                    
            logger.info(f"PID file updated: {self.pid_file}")
        except Exception as e:
            logger.error(f"Error updating PID file: {e}")
    
    def get_all_pids(self):
        """모든 PID 정보 조회"""
        if not os.path.exists(self.pid_file):
            return {}
            
        try:
            with open(self.pid_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading PID file: {e}")
            return {} 