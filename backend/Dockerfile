FROM python:3.11-slim

# 로케일 설정 추가 (한글 파일명 지원)
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUTF8=1

WORKDIR /app

# 시스템 패키지 설치 (PDF 처리용 추가)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-kor \
    locales \
    && rm -rf /var/lib/apt/lists/*

# 로케일 생성 (한글 지원)
RUN locale-gen ko_KR.UTF-8
RUN locale-gen en_US.UTF-8
ENV LANG=ko_KR.UTF-8
ENV LC_ALL=ko_KR.UTF-8
ENV LC_CTYPE=ko_KR.UTF-8

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# PYTHONPATH 환경변수 설정 (컨테이너 내에서 import 경로 문제 방지)
ENV PYTHONPATH=/app

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 