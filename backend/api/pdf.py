from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from services.pdf_processor import PolicyProcessor
from typing import Optional

router = APIRouter()

@router.post("/users/pdf/process",
    summary="PDF 보험조항 추출",
    description="보험 약관 PDF 파일을 업로드하여 AI 기반으로 보험 조항을 추출합니다. 진단서 기반 보험금 산정에 필요한 특약 정보를 자동으로 분석합니다.",
    response_description="추출된 보험조항 목록")
async def extract_insurance_clauses(file: UploadFile = File(..., description="보험 약관 PDF 파일"), db: Session = Depends(get_db)):
    """
    PDF에서 보험조항 추출
    - 보험 약관 PDF 파일 업로드 및 AI 기반 조항 추출
    - Swagger에서 있어보이는 기능
    """
    try:
        # TODO: PDF 파일 검증
        # TODO: PDF 처리 서비스 호출
        # TODO: AI 기반 조항 추출
        # TODO: 결과 반환
        
        return {
            "message": "PDF 조항 추출 완료",
            "extracted_clauses": [
                {
                    "clause_code": "H001",
                    "clause_name": "입원일당",
                    "per_unit": 50000,
                    "max_total": 1000000
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 추출 실패: {str(e)}")

@router.get("/users/pdf/process/{extraction_id}",
    summary="PDF 추출 결과 조회",
    description="PDF 추출 작업의 결과를 조회합니다. 추출 완료 후 결과를 확인할 수 있습니다.",
    response_description="추출 결과")
async def get_extraction_result(extraction_id: int, db: Session = Depends(get_db)):
    """
    PDF 추출 결과 조회
    - 추출 완료 후 결과 확인용
    """
    try:
        # TODO: 추출 결과 조회
        # TODO: 결과 반환
        
        return {
            "extraction_id": extraction_id,
            "status": "completed",
            "extracted_clauses": [
                {
                    "clause_code": "H001",
                    "clause_name": "입원일당",
                    "per_unit": 50000,
                    "max_total": 1000000
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추출 결과 조회 실패: {str(e)}") 