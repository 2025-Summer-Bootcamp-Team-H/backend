from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from typing import Optional

router = APIRouter()

@router.post("/diagnoses/images", 
    summary="진단서 이미지 업로드",
    description="진단서 이미지 파일을 업로드하고 데이터베이스에 진단서 레코드를 생성합니다. 업로드 후 생성된 진단서 ID를 반환합니다.",
    response_description="업로드 성공 시 진단서 ID 반환")
async def upload_diagnosis(file: UploadFile = File(..., description="진단서 이미지 파일 (JPG, PNG, PDF 등)"), db: Session = Depends(get_db)):
    """
    진단서 이미지 업로드
    - 파일 업로드 후 DB에 진단서 레코드 생성
    - 생성된 PK 반환
    """
    try:
        # TODO: 파일 검증 로직
        # TODO: 파일 저장 로직
        # TODO: DB에 진단서 레코드 생성
        # TODO: 생성된 PK 반환
        
        return {"message": "진단서 업로드 성공", "diagnosis_id": 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")

@router.post("/receipts/images",
    summary="영수증 이미지 업로드",
    description="영수증 이미지 파일을 업로드하고 데이터베이스에 영수증 레코드를 생성합니다. 업로드 후 생성된 영수증 ID를 반환합니다.",
    response_description="업로드 성공 시 영수증 ID 반환")
async def upload_receipt(file: UploadFile = File(..., description="영수증 이미지 파일 (JPG, PNG, PDF 등)"), db: Session = Depends(get_db)):
    """
    영수증 이미지 업로드
    - 파일 업로드 후 DB에 영수증 레코드 생성
    - 생성된 PK 반환
    """
    try:
        # TODO: 파일 검증 로직
        # TODO: 파일 저장 로직
        # TODO: DB에 영수증 레코드 생성
        # TODO: 생성된 PK 반환
        
        return {"message": "영수증 업로드 성공", "receipt_id": 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}") 