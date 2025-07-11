#!/usr/bin/env python3
"""
설정 파일 - API 키 및 폴더 경로 관리
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 자동 로드
load_dotenv()

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent

# 폴더 경로 설정
INPUT_PDFS_DIR = PROJECT_ROOT / "input_pdfs"
OUTPUT_RESULTS_DIR = PROJECT_ROOT / "output_results"

# 폴더가 없으면 생성
INPUT_PDFS_DIR.mkdir(exist_ok=True)
OUTPUT_RESULTS_DIR.mkdir(exist_ok=True)

# AI API 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# AI 모델 선택 (gpt-4o, claude-3-5-sonnet, gpt-4-turbo)
DEFAULT_AI_MODEL = "claude-3-5-sonnet"  # Claude 3.5 Sonnet을 기본으로 설정

# 보험사 설정
DEFAULT_INSURANCE_COMPANY = "samsung"  # 기본 보험사

# 추출 설정
MAX_CLAUSES_TO_PROCESS = 50  # AI로 처리할 최대 특약 수
CONFIDENCE_THRESHOLD = 0.7   # 고신뢰도 기준

# 파일 확장자
SUPPORTED_FILE_TYPES = ['.pdf']

# 로깅 설정
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def get_openai_api_key():
    """OpenAI API 키를 반환합니다."""
    if not OPENAI_API_KEY:
        raise ValueError(
            "OpenAI API 키가 설정되지 않았습니다.\n"
            "다음 중 하나의 방법으로 설정하세요:\n"
            "1. 환경변수 설정: set OPENAI_API_KEY=your_api_key_here\n"
            "2. config.py 파일에서 직접 설정\n"
            "3. .env 파일 생성 (권장)"
        )
    return OPENAI_API_KEY

def get_anthropic_api_key():
    """Anthropic API 키를 반환합니다."""
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "Anthropic API 키가 설정되지 않았습니다.\n"
            "다음 중 하나의 방법으로 설정하세요:\n"
            "1. 환경변수 설정: set ANTHROPIC_API_KEY=your_api_key_here\n"
            "2. config.py 파일에서 직접 설정\n"
            "3. .env 파일 생성 (권장)"
        )
    return ANTHROPIC_API_KEY

def setup_env_file():
    """환경변수 파일을 생성합니다."""
    env_file = PROJECT_ROOT / ".env"
    
    if not env_file.exists():
        env_content = """# AI API 키 설정
# OpenAI API 키 (https://platform.openai.com/api-keys 에서 발급받으세요)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API 키 (https://console.anthropic.com/ 에서 발급받으세요)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 기타 설정
DEFAULT_INSURANCE_COMPANY=samsung
DEFAULT_AI_MODEL=claude-3-5-sonnet
"""
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"✅ .env 파일이 생성되었습니다: {env_file}")
        print("📝 .env 파일에서 API 키들을 설정하세요")
    
    return env_file 