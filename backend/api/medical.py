from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from models.schemas import MedicalDiagnosisCreate, MedicalReceiptCreate
from typing import Optional

router = APIRouter()

# 진단서 관련 API
@router.patch("/diagnoses/{diagnosis_id}")
async def update_diagnosis(diagnosis_id: int, data: dict, db: Session = Depends(get_db)):
    """
    진단서 정보 수정후 저장
    - 사용자가 OCR 결과를 수정할 수 있음
    """
    try:
        # TODO: 진단서 조회
        # TODO: 데이터 검증
        # TODO: DB 업데이트
        
        return {"message": "진단서 수정 완료", "diagnosis_id": diagnosis_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단서 수정 실패: {str(e)}")

@router.get("/diagnoses/{diagnosis_id}")
async def get_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    """
    진단서 정보 조회
    - 수정 페이지에서 현재 정보 표시용
    """
    try:
        # TODO: 진단서 조회
        # TODO: 데이터 반환
        
        return {"diagnosis_id": diagnosis_id, "patient_name": "홍길동", "diagnosis_name": "감기"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단서 조회 실패: {str(e)}")

# 영수증 관련 API
@router.patch("/receipts/{receipt_id}")
async def update_receipt(receipt_id: int, data: dict, db: Session = Depends(get_db)):
    """
    영수증 정보 수정후 저장
    - 사용자가 OCR 결과를 수정할 수 있음
    """
    try:
        # TODO: 영수증 조회
        # TODO: 데이터 검증
        # TODO: DB 업데이트
        
        return {"message": "영수증 수정 완료", "receipt_id": receipt_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영수증 수정 실패: {str(e)}")

@router.get("/receipts/{receipt_id}")
async def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """
    영수증 정보 조회
    - 수정 페이지에서 현재 정보 표시용
    """
    try:
        # TODO: 영수증 조회
        # TODO: 데이터 반환
        
        return {"receipt_id": receipt_id, "hospital_name": "삼성병원", "total_amount": 50000}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영수증 조회 실패: {str(e)}") 