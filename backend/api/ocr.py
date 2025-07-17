from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

router = APIRouter()

# Pydantic 모델
class DiagnosisUpdate(BaseModel):
    patient_name: Optional[str] = None
    patient_ssn: Optional[str] = None
    diagnosis_name: Optional[str] = None
    diagnosis_date: Optional[date] = None  # date 타입 사용
    diagnosis_text: Optional[str] = None
    hospital_name: Optional[str] = None
    doctor_name: Optional[str] = None
    icd_code: Optional[str] = None
    admission_days: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_name": "홍길동",
                "patient_ssn": "900101-1234567",
                "diagnosis_name": "감기",
                "diagnosis_date": "2024-07-16",
                "diagnosis_text": "기침, 발열",
                "hospital_name": "서울병원",
                "doctor_name": "김의사",
                "icd_code": "J00",
                "admission_days": 3
            }
        }
    )

class ReceiptUpdate(BaseModel):
    patient_name: Optional[str] = None
    treatment_date: Optional[date] = None  # origin/main의 필드명 사용
    hospital_name: Optional[str] = None
    total_amount: Optional[float] = None
    insurance_amount: Optional[float] = None  # origin/main의 새 필드
    patient_payment: Optional[float] = None   # origin/main의 새 필드
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_name": "홍길동",
                "treatment_date": "2024-07-16",
                "hospital_name": "서울병원",
                "total_amount": 50000,
                "insurance_amount": 40000,
                "patient_payment": 10000
            }
        }
    )

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

# HEAD에 있던 추가 함수들을 유지 (필요한 경우)
@router.patch("/diagnoses/{diagnosis_id}",
    summary="진단서 정보 수정",
    description="진단서의 정보를 수동으로 수정하고 데이터베이스에 저장합니다.",
    response_description="수정 완료 메시지")
async def update_diagnosis(diagnosis_id: int, diagnosis_data: DiagnosisUpdate, db: Session = Depends(get_db)):
    """
    진단서 정보 수정후 저장
    """
    try:
        diagnosis = db.query(MedicalDiagnosis).filter(
            MedicalDiagnosis.id == diagnosis_id,
            MedicalDiagnosis.is_deleted == False
        ).first()

        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다.")

        update_fields = diagnosis_data.model_dump(exclude_unset=True)

        # date 타입은 자동으로 처리됨 (Pydantic이 자동 변환)
        for field, value in update_fields.items():
            setattr(diagnosis, field, value)

        db.commit()
        db.refresh(diagnosis)

        return {"message": "진단서 정보 수정 완료", "diagnosis_id": diagnosis_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단서 정보 수정 실패: {str(e)}")

# ... 나머지 함수들도 유사하게 유지