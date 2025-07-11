#!/usr/bin/env python3
"""
환경 설정 테스트 스크립트
팀원들이 프로젝트 설정이 올바른지 확인할 수 있습니다.
"""

import os
import sys
import requests
from sqlalchemy import create_engine, text
import redis

def test_database_connection():
    """데이터베이스 연결 테스트"""
    try:
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/insurance_system")
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ 데이터베이스 연결 성공")
            return True
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False

def test_redis_connection():
    """Redis 연결 테스트"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Redis 연결 성공")
        return True
    except Exception as e:
        print(f"❌ Redis 연결 실패: {e}")
        return False

def test_api_server():
    """API 서버 연결 테스트"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API 서버 연결 성공")
            return True
        else:
            print(f"❌ API 서버 응답 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 서버 연결 실패: {e}")
        return False

def test_environment_variables():
    """환경 변수 테스트"""
    required_vars = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", 
        "SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  누락된 환경 변수: {', '.join(missing_vars)}")
        print("   env.example 파일을 참고하여 .env 파일을 설정하세요.")
        return False
    else:
        print("✅ 모든 필수 환경 변수 설정됨")
        return True

def test_file_structure():
    """파일 구조 테스트"""
    required_files = [
        "backend/main.py",
        "backend/requirements.txt",
        "docker-compose.yml",
        "backend/utils/scripts/create_final_dummy_data.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 누락된 파일: {', '.join(missing_files)}")
        return False
    else:
        print("✅ 모든 필수 파일 존재")
        return True

def main():
    """메인 테스트 함수"""
    print("🔍 환경 설정 테스트 시작...\n")
    
    tests = [
        ("파일 구조", test_file_structure),
        ("환경 변수", test_environment_variables),
        ("데이터베이스 연결", test_database_connection),
        ("Redis 연결", test_redis_connection),
        ("API 서버", test_api_server)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"테스트: {test_name}")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! 개발을 시작할 수 있습니다.")
        return True
    else:
        print("⚠️  일부 테스트 실패. 위의 오류를 수정한 후 다시 시도하세요.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 