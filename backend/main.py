from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import os

from models.database import get_db, engine
from models.models import Base
from api import upload, ocr, medical, forgeries, claims, admin, pdf, auth

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

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

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
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
v1_router.include_router(admin.router, tags=["👨‍💼 관리자"])
v1_router.include_router(pdf.router, tags=["📄 PDF 처리"])

# 메인 앱에 v1 라우터 등록
app.include_router(v1_router)

# 기본 라우트들
@app.get("/")
async def root():
    return {"message": "Insurance Claim System API"}

@app.get("/health")
async def health_check():
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 