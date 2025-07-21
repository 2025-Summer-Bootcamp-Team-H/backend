from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import os

from models.database import get_db, engine
from models.models import Base
from api import upload, ocr, medical, forgeries, claims, pdf, auth, image

# 필수 환경변수 검증
def validate_environment():
    """필수 환경변수 검증"""
    required_vars = [
        "JWT_SECRET_KEY",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")

# 환경변수 검증 실행
try:
    validate_environment()
except ValueError as e:
    print(f"❌ 환경변수 오류: {e}")
    print("💡 .env 파일을 확인하고 필수 환경변수를 설정하세요.")
    raise

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from models.database import engine # SQLAlchemy engine 가져오기

# OpenTelemetry 설정
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()

# OTLP Exporter 설정 (Jaeger로 데이터 전송)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://localhost:4318/v1/traces")
)
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# 데이터베이스 테이블 생성
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI 보험금 청구 시스템 API",
    description="AI 기반 보험금 청구 처리 시스템 - PDF에서 보험 조항을 추출하고 진단서를 분석하여 자동으로 보험금을 계산합니다.",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "📄 PDF 처리", 
            "description": "보험 약관 PDF 파일 업로드 및 AI 기반 조항 추출"
        },
        {
            "name": "🏥 의료 정보",
            "description": "고객 진단서 및 영수증 정보 관리"
        },
        {
            "name": "💰 보험금 청구",
            "description": "보험금 청구 및 계산 처리"
        }
    ]
)

# CORS 설정 - 환경변수에서 가져오기
def get_cors_origins():
    """환경변수에서 CORS 허용 오리진을 가져옵니다."""
    # 기본값 (개발 환경)
    default_origins = ["http://localhost:3000", "http://frontend:3000"]
    
    # 환경변수에서 가져오기
    allowed_origins = os.getenv("ALLOWED_ORIGINS")
    if allowed_origins:
        # 쉼표로 구분된 문자열을 리스트로 변환
        origins = [origin.strip() for origin in allowed_origins.split(",")]
        return origins
    
    # 개별 환경변수 확인
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        return [frontend_url] + default_origins
    
    return default_origins

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 라우터 생성
v1_router = APIRouter(prefix="/api/v1")

# v1 하위에 라우터들 등록
v1_router.include_router(auth.router, tags=["🔐 인증"])
v1_router.include_router(upload.router, tags=["📤 업로드"])
v1_router.include_router(ocr.router, tags=["🔍 OCR 처리"])
v1_router.include_router(medical.router, tags=["🏥 의료 정보"])
v1_router.include_router(forgeries.router, tags=["🔍 위조분석"])
v1_router.include_router(claims.router, tags=["💰 청구"])
v1_router.include_router(pdf.router, tags=["📄 PDF 처리"])
v1_router.include_router(image.router, tags=["🖼️ 이미지"])

# 메인 앱에 v1 라우터 등록
app.include_router(v1_router)

# FastAPI 애플리케이션 계측
FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
# SQLAlchemy 계측
SQLAlchemyInstrumentor().instrument(engine=engine)
# Psycopg2 계측
Psycopg2Instrumentor().instrument()


# 기본 라우트들
@app.get("/")
async def root():
    return {"message": "Insurance Claim System API"}

@app.get("/health")
async def health_check():
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/config")
async def get_config():
    """환경 설정 정보를 반환합니다 (디버깅용)"""
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "cors_origins": get_cors_origins(),
        "frontend_url": os.getenv("FRONTEND_URL"),
        "database_url": os.getenv("DATABASE_URL", "not_set"),
        "storage_type": os.getenv("STORAGE_TYPE", "local"),
        "upload_dir": os.getenv("UPLOAD_DIR", "./uploads"),
        "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "jwt_secret_set": bool(os.getenv("JWT_SECRET_KEY")),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 