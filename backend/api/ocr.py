from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

# Pydantic 모델
class DiagnosisUpdate(BaseModel):
    diagnosis_name: Optional[str] = None
    diagnosis_date: Optional[str] = None
    hospital_name: Optional[str] = None
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None
    patient_ssn: Optional[str] = None

class ReceiptUpdate(BaseModel):
    hospital_name: Optional[str] = None
    treatment_date: Optional[str] = None
    total_amount: Optional[float] = None
    insurance_amount: Optional[float] = None
    patient_payment: Optional[float] = None

@router.patch("/diagnoses/ocr/{diagnosis_id}",
    summary="진단서 OCR 처리",
    description="AI를 사용하여 진단서 이미지에서 텍스트를 추출하고 진단 정보를 자동으로 인식하여 데이터베이스에 저장합니다.",
    response_description="OCR 처리 완료 메시지")
async def ocr_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    """
    진단서 OCR 실행후 저장
    - AI API 호출하여 OCR 처리
    - 추출된 정보를 DB에 업데이트
    """
    try:
        # TODO: 진단서 이미지 조회
        # TODO: AI API 호출 (OpenAI/Anthropic)
        # TODO: OCR 결과 파싱
        # TODO: DB에 정보 업데이트
        
        return {"message": "진단서 OCR 처리 완료", "diagnosis_id": diagnosis_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 실패: {str(e)}")

@router.patch("/receipts/ocr/{receipt_id}",
    summary="영수증 OCR 처리",
    description="AI를 사용하여 영수증 이미지에서 텍스트를 추출하고 의료비 정보를 자동으로 인식하여 데이터베이스에 저장합니다.",
    response_description="OCR 처리 완료 메시지")
async def ocr_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """
    영수증 OCR 실행후 저장
    - AI API 호출하여 OCR 처리
    - 추출된 정보를 DB에 업데이트
    """
    try:
        # TODO: 영수증 이미지 조회
        # TODO: AI API 호출 (OpenAI/Anthropic)
        # TODO: OCR 결과 파싱
        # TODO: DB에 정보 업데이트
        
        return {"message": "영수증 OCR 처리 완료", "receipt_id": receipt_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 실패: {str(e)}")

@router.patch("/diagnoses/{diagnosis_id}",
    summary="진단서 정보 수정",
    description="진단서의 정보를 수동으로 수정하고 데이터베이스에 저장합니다.",
    response_description="수정 완료 메시지")
async def update_diagnosis(diagnosis_id: int, diagnosis_data: DiagnosisUpdate, db: Session = Depends(get_db)):
    """
    진단서 정보 수정후 저장
    """
    try:
        # TODO: 진단서 조회
        # TODO: 정보 업데이트
        # TODO: DB에 저장
        
        return {"message": "진단서 정보 수정 완료", "diagnosis_id": diagnosis_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단서 정보 수정 실패: {str(e)}")

@router.patch("/receipts/{receipt_id}",
    summary="영수증 정보 수정",
    description="영수증의 정보를 수동으로 수정하고 데이터베이스에 저장합니다.",
    response_description="수정 완료 메시지")
async def update_receipt(receipt_id: int, receipt_data: ReceiptUpdate, db: Session = Depends(get_db)):
    """
    영수증 정보 수정후 저장
    """
    try:
        # TODO: 영수증 조회
        # TODO: 정보 업데이트
        # TODO: DB에 저장
        
        return {"message": "영수증 정보 수정 완료", "receipt_id": receipt_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영수증 정보 수정 실패: {str(e)}")

@router.get("/diagnoses/{diagnosis_id}",
    summary="진단서 정보 조회",
    description="진단서의 상세 정보를 조회합니다.",
    response_description="진단서 상세 정보")
async def get_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    """
    진단서 정보 조회
    """
    try:
        # TODO: 진단서 정보 조회
        # TODO: 결과 반환
        
        return {
            "diagnosis_id": diagnosis_id,
            "diagnosis_name": "감기",
            "diagnosis_date": "2024-01-15",
            "hospital_name": "삼성병원",
            "doctor_name": "김의사",
            "patient_name": "홍길동",
            "patient_ssn": "123456-1234567"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단서 정보 조회 실패: {str(e)}")

@router.get("/receipts/{receipt_id}",
    summary="영수증 정보 조회",
    description="영수증의 상세 정보를 조회합니다.",
    response_description="영수증 상세 정보")
async def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """
    영수증 정보 조회
    """
    try:
        # TODO: 영수증 정보 조회
        # TODO: 결과 반환
        
        return {
            "receipt_id": receipt_id,
            "hospital_name": "삼성병원",
            "treatment_date": "2024-01-15",
            "total_amount": 50000,
            "insurance_amount": 40000,
            "patient_payment": 10000
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영수증 정보 조회 실패: {str(e)}") 