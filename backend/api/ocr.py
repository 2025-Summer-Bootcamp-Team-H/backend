from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Pydantic 모델
class DiagnosisUpdate(BaseModel):
    patient_name: Optional[str] = None
    patient_ssn: Optional[str] = None
    diagnosis_name: Optional[str] = None
    diagnosis_date: Optional[str] = None  # "YYYY-MM-DD"
    diagnosis_text: Optional[str] = None
    hospital_name: Optional[str] = None
    doctor_name: Optional[str] = None
    icd_code: Optional[str] = None
    admission_days: Optional[int] = None
    image_url: Optional[str] = None

class ReceiptUpdate(BaseModel):
    patient_name: Optional[str] = None
    receipt_date: Optional[str] = None
    hospital_name: Optional[str] = None
    total_amount: Optional[float] = None
    treatment_details: Optional[str] = None
    image_url: Optional[str] = None

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
        diagnosis = db.query(MedicalDiagnosis).filter(
            MedicalDiagnosis.id == diagnosis_id,
            MedicalDiagnosis.is_deleted == False
        ).first()

        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다.")

        update_fields = diagnosis_data.model_dump(exclude_unset=True)

        # 이미지 주소는 수정하지 않음
        if "image_url" in update_fields:
            del update_fields["image_url"]

        if "diagnosis_date" in update_fields and update_fields["diagnosis_date"]:
            try:
                update_fields["diagnosis_date"] = datetime.strptime(update_fields["diagnosis_date"], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식은 YYYY-MM-DD이어야 합니다.")

        for field, value in update_fields.items():
            setattr(diagnosis, field, value)

        db.commit()
        db.refresh(diagnosis)

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
        receipt = db.query(MedicalReceipt).filter(
            MedicalReceipt.id == receipt_id,
            MedicalReceipt.is_deleted == False
        ).first()

        if not receipt:
            raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다.")

        update_fields = receipt_data.model_dump(exclude_unset=True)

        # 이미지 주소는 수정하지 않음
        if "image_url" in update_fields:
            del update_fields["image_url"]

        if "receipt_date" in update_fields and update_fields["receipt_date"]:
            try:
                update_fields["receipt_date"] = datetime.strptime(update_fields["receipt_date"], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식은 YYYY-MM-DD이어야 합니다.")

        for field, value in update_fields.items():
            setattr(receipt, field, value)

        db.commit()
        db.refresh(receipt)

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
        diagnosis = db.query(MedicalDiagnosis).filter(
            MedicalDiagnosis.id == diagnosis_id,
            MedicalDiagnosis.is_deleted == False
        ).first()

        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다.")

        return {
            "diagnosis_id": diagnosis.id,
            "user_id": diagnosis.user_id,
            "patient_name": diagnosis.patient_name,
            "patient_ssn": diagnosis.patient_ssn,
            "diagnosis_name": diagnosis.diagnosis_name,
            "diagnosis_date": str(diagnosis.diagnosis_date),
            "diagnosis_text": diagnosis.diagnosis_text,
            "hospital_name": diagnosis.hospital_name,
            "doctor_name": diagnosis.doctor_name,
            "icd_code": diagnosis.icd_code,
            "admission_days": diagnosis.admission_days,
            "image_url": diagnosis.image_url,
            "created_at": str(diagnosis.created_at),
            "updated_at": str(diagnosis.updated_at),
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
        receipt = db.query(MedicalReceipt).filter(
            MedicalReceipt.id == receipt_id,
            MedicalReceipt.is_deleted == False
        ).first()

        if not receipt:
            raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다.")

        return {
            "receipt_id": receipt.id,
            "user_id": receipt.user_id,
            "patient_name": receipt.patient_name,
            "receipt_date": str(receipt.receipt_date),
            "hospital_name": receipt.hospital_name,
            "total_amount": receipt.total_amount,
            "treatment_details": receipt.treatment_details,
            "image_url": receipt.image_url,
            "created_at": str(receipt.created_at),
            "updated_at": str(receipt.updated_at),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영수증 정보 조회 실패: {str(e)}")