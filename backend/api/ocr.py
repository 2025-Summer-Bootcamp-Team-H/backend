from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
import os
import base64
from openai import OpenAI
from .medical import DiagnosisUpdate, ReceiptUpdate

router = APIRouter()

UPSTAGE_OCR_API_KEY = os.getenv("UPSTAGE_OCR_API_KEY")
UPSTAGE_OCR_API_URL = "https://api.upstage.ai/v1/information-extraction"

client = OpenAI(
    api_key=UPSTAGE_OCR_API_KEY,
    base_url=UPSTAGE_OCR_API_URL
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")

def encode_img_to_base64(img_path):
    with open(img_path, 'rb') as img_file:
        img_bytes = img_file.read()
        return base64.b64encode(img_bytes).decode('utf-8')

# 진단서 정보 추출용 JSON 스키마
diagnosis_schema = {
    "name": "diagnosis_schema",
    "schema": {
        "type": "object",
        "properties": {
            "patient_name": {"type": "string", "description": "환자 이름 (한글)"},
            "patient_ssn": {"type": "string", "description": "주민등록번호 (하이픈 포함)"},
            "diagnosis_name": {"type": "string", "description": "진단명"},
            "diagnosis_date": {"type": "string", "description": "진단일자 (YYYY-MM-DD)"},
            "diagnosis_text": {"type": "string", "description": "진단 내용 요약"},
            "hospital_name": {"type": "string", "description": "병원명"},
            "doctor_name": {"type": "string", "description": "의사 이름"},
            "icd_code": {"type": "string", "description": "ICD 코드"},
            "admission_days": {"type": "integer", "description": "입원 일수 (외래인 경우 0)"}
        }
    }
}

# 영수증 정보 추출용 JSON 스키마
receipt_schema = {
    "name": "receipt_schema",
    "schema": {
        "type": "object",
        "properties": {
            "patient_name": {"type": "string", "description": "환자 이름 (한글)"},
            "receipt_date": {"type": "string", "description": "진료일자 (YYYY-MM-DD)"},
            "hospital_name": {"type": "string", "description": "병원명"},
            "total_amount": {"type": "number", "description": "총 진료비"},
            "treatment_details": {"type": "string", "description": "진료 상세내역"}
        }
    }
}

@router.patch("/diagnoses/ocr/{diagnosis_id}",
    summary="진단서 정보 추출 (Upstage Information Extraction API)",
    description="Upstage Information Extraction API를 사용하여 진단서 이미지에서 주요 정보를 추출하고 DB에 저장합니다.",
    response_description="OCR 정보 추출 완료 메시지")
async def ocr_diagnosis_extract(diagnosis_id: int, db: Session = Depends(get_db)):
    try:
        diagnosis = db.query(MedicalDiagnosis).filter(
            MedicalDiagnosis.id == diagnosis_id,
            MedicalDiagnosis.is_deleted == False
        ).first()
        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다.")
        if not diagnosis.image_url:
            raise HTTPException(status_code=400, detail="진단서 이미지가 업로드되지 않았습니다.")
        file_path = os.path.join(UPLOAD_DIR, "diagnosis", os.path.basename(diagnosis.image_url))
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="이미지 파일이 존재하지 않습니다.")
        base64_data = encode_img_to_base64(file_path)
        extraction_response = client.chat.completions.create(
            model="information-extract",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:application/octet-stream;base64,{base64_data}"}
                        }
                    ]
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": diagnosis_schema
            }
        )
        fields = extraction_response.choices[0].message.content
        print("Upstage 응답:", fields)  # 응답값 로그 출력
        import json
        parsed = json.loads(fields)
        # 날짜 및 admission_days 처리
        if parsed.get("diagnosis_date"):
            try:
                parsed["diagnosis_date"] = datetime.strptime(parsed["diagnosis_date"], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")
        if "admission_days" in parsed:
            try:
                parsed["admission_days"] = int(parsed["admission_days"])
            except (ValueError, TypeError):
                parsed["admission_days"] = 0
        for key, value in parsed.items():
            if hasattr(diagnosis, key):
                setattr(diagnosis, key, value)
        db.commit()
        db.refresh(diagnosis)
        return {"message": "진단서 정보 추출 완료 (Upstage Information Extraction)", "diagnosis_id": diagnosis_id, "data": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단서 정보 추출 실패: {str(e)}")

@router.patch("/receipts/ocr/{receipt_id}",
    summary="영수증 정보 추출 (Upstage Information Extraction API)",
    description="Upstage Information Extraction API를 사용하여 영수증 이미지에서 주요 정보를 추출하고 DB에 저장합니다.",
    response_description="OCR 정보 추출 완료 메시지")
async def ocr_receipt_extract(receipt_id: int, db: Session = Depends(get_db)):
    try:
        receipt = db.query(MedicalReceipt).filter(
            MedicalReceipt.id == receipt_id,
            MedicalReceipt.is_deleted == False
        ).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다.")
        if not receipt.image_url:
            raise HTTPException(status_code=400, detail="영수증 이미지가 업로드되지 않았습니다.")
        file_path = os.path.join(UPLOAD_DIR, "receipts", os.path.basename(receipt.image_url))
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="이미지 파일이 존재하지 않습니다.")
        base64_data = encode_img_to_base64(file_path)
        extraction_response = client.chat.completions.create(
            model="information-extract",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:application/octet-stream;base64,{base64_data}"}
                        }
                    ]
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": receipt_schema
            }
        )
        fields = extraction_response.choices[0].message.content
        print("Upstage 응답:", fields)  # 응답값 로그 출력
        import json
        parsed = json.loads(fields)
        # 날짜 및 total_amount 처리
        if parsed.get("receipt_date"):
            try:
                parsed["receipt_date"] = datetime.strptime(parsed["receipt_date"], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")
        if "total_amount" in parsed:
            try:
                parsed["total_amount"] = float(parsed["total_amount"])
            except (ValueError, TypeError):
                parsed["total_amount"] = 0.0
        for key, value in parsed.items():
            if hasattr(receipt, key):
                setattr(receipt, key, value)
        db.commit()
        db.refresh(receipt)
        return {"message": "영수증 정보 추출 완료 (Upstage Information Extraction)", "receipt_id": receipt_id, "data": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영수증 정보 추출 실패: {str(e)}")

# 기존 수동 수정 기능 유지
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

        for field, value in update_fields.items():
            setattr(receipt, field, value)

        db.commit()
        db.refresh(receipt)

        return {"message": "영수증 정보 수정 완료", "receipt_id": receipt_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영수증 정보 수정 실패: {str(e)}")