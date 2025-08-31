#!/usr/bin/env python3
"""
비밀번호 암호화 및 INSERT 문 생성 도구
Java의 PBKDF2PasswordEncoder와 동일한 알고리즘 사용
"""

import hashlib
import secrets
import base64
import sys
import hmac
import struct

def pbkdf2_hmac_sha256(password, salt, iterations=100000, key_length=32):
    """
    PBKDF2-HMAC-SHA256 구현
    Java의 PBKDF2PasswordEncoder와 동일한 결과 생성
    """
    # password를 bytes로 변환
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # PBKDF2 구현
    key = b''
    block_num = 1
    
    while len(key) < key_length:
        # U1 = HMAC-SHA256(password, salt || block_num)
        block = salt + struct.pack('>I', block_num)
        u = hmac.new(password, block, hashlib.sha256).digest()
        result = u
        
        # U2, U3, ... Uc 계산
        for i in range(2, iterations + 1):
            u = hmac.new(password, u, hashlib.sha256).digest()
            result = bytes(a ^ b for a, b in zip(result, u))
        
        key += result
        block_num += 1
    
    return key[:key_length]

def hash_password(password):
    """
    비밀번호를 PBKDF2로 해싱
    Java의 PBKDF2PasswordEncoder와 동일한 형식으로 반환
    """
    # 32바이트 랜덤 salt 생성
    salt = secrets.token_bytes(32)
    
    # PBKDF2 해싱
    hash_bytes = pbkdf2_hmac_sha256(password, salt)
    
    # salt + hash를 결합
    combined = salt + hash_bytes
    
    # Base64 인코딩
    return base64.b64encode(combined).decode('utf-8')

def verify_password(password, stored_hash):
    """
    비밀번호 검증
    """
    try:
        # Base64 디코딩
        combined = base64.b64decode(stored_hash)
        
        # salt와 hash 분리 (첫 32바이트 = salt, 나머지 32바이트 = hash)
        salt = combined[:32]
        stored_hash_bytes = combined[32:]
        
        # 입력된 비밀번호로 해싱
        computed_hash = pbkdf2_hmac_sha256(password, salt)
        
        # 해시 비교
        return hmac.compare_digest(stored_hash_bytes, computed_hash)
    except Exception:
        return False

def generate_insert_sql(user_id, password, user_nm, role, company_id):
    """
    INSERT SQL 문 생성
    """
    hashed_password = hash_password(password)
    
    sql = f"""INSERT INTO users (user_id, user_pwd, user_nm, role, company_id)
VALUES ('{user_id}', '{hashed_password}', '{user_nm}', '{role}', '{company_id}');"""
    
    return sql, hashed_password

def main():
    if len(sys.argv) != 6:
        print("사용법: python user_generator.py <user_id> <password> <user_nm> <role> <company_id>")
        print("예시: python user_generator.py testuser password123 '테스트 사용자' USER company1")
        return
    
    user_id = sys.argv[1]
    password = sys.argv[2]
    user_nm = sys.argv[3]
    role = sys.argv[4]
    company_id = sys.argv[5]
    
    # INSERT SQL 생성
    sql, hashed_password = generate_insert_sql(user_id, password, user_nm, role, company_id)

    print(sql)
    
    # 검증 테스트
    print("\n=== 해쉬 테스트 ===")
    is_valid = verify_password(password, hashed_password)
    print(f"비밀번호 검증 결과: {'성공' if is_valid else '실패'}")

if __name__ == "__main__":
    main()
