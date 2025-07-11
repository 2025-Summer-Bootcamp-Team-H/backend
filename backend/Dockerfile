FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치 (PDF 처리용 추가)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-kor \
    && rm -rf /var/lib/apt/lists/*

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