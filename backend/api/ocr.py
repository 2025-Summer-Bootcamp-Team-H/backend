from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
import os
import base64
import json
import re
from openai import OpenAI
import requests
from services.storage_service import storage_service

router = APIRouter()

# Upstage API 키 환경변수에서 불러오기
UPSTAGE_OCR_API_KEY = os.getenv("UPSTAGE_OCR_API_KEY")
if not UPSTAGE_OCR_API_KEY:
    raise ValueError("UPSTAGE_OCR_API_KEY 환경변수가 설정되지 않았습니다.")

# Upstage Information Extraction API URL
UPSTAGE_OCR_API_URL = "https://api.upstage.ai/v1/information-extraction"

# OpenAI 클라이언트 설정
client = OpenAI(
    api_key=UPSTAGE_OCR_API_KEY,
    base_url=UPSTAGE_OCR_API_URL
)

# 환경변수에서 업로드 디렉토리 설정
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")

# Pydantic 모델들 (기존 기능 유지)
class DiagnosisUpdate(BaseModel):
    patient_name: Optional[str] = None
    patient_ssn: Optional[str] = None
    diagnosis_name: Optional[str] = None
    diagnosis_date: Optional[date] = None
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
    receipt_date: Optional[date] = None
    hospital_name: Optional[str] = None
    total_amount: Optional[float] = None
    treatment_details: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_name": "홍길동",
                "receipt_date": "2024-07-16",
                "hospital_name": "서울병원",
                "total_amount": 50000,
                "treatment_details": "진료비 상세내역"
            }
        }
    )

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
        },
        "required": ["patient_name", "diagnosis_name", "hospital_name"]
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
            "treatment_details": {"type": "string", "description": "진료 상세내역 (예: 기본 진찰료, 검사료, 방사선 치료료) - 금액 정보 제외하고 항목명만 간단히 나열, 쉼표로 구분"}
        },
        "required": ["patient_name", "hospital_name", "total_amount"]
    }
}

@router.patch("/diagnoses/ocr/{diagnosis_id}",
    summary="진단서 OCR 처리",
    description="AI를 사용하여 진단서 이미지에서 텍스트를 추출하고 진단 정보를 자동으로 인식하여 데이터베이스에 저장합니다.",
    response_description="OCR 처리 완료 메시지")
async def ocr_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    try:
        diagnosis = db.query(MedicalDiagnosis).filter(
            MedicalDiagnosis.id == diagnosis_id,
            MedicalDiagnosis.is_deleted == False
        ).first()
        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다.")
        if not diagnosis.image_url:
            raise HTTPException(status_code=400, detail="진단서 이미지가 업로드되지 않았습니다.")

        # 스토리지 서비스를 사용하여 파일 읽기
        try:
            if diagnosis.image_url.startswith('http'):
                # S3 URL인 경우
                response = requests.get(diagnosis.image_url)
                response.raise_for_status()
                image_data = response.content
            else:
                # 로컬 파일인 경우
                file_path = os.path.join(UPLOAD_DIR, "diagnosis", os.path.basename(diagnosis.image_url))
                if not os.path.exists(file_path):
                    raise HTTPException(status_code=404, detail="이미지 파일이 존재하지 않습니다.")
                with open(file_path, 'rb') as f:
                    image_data = f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"이미지 파일 읽기 실패: {str(e)}")

        image_b64 = base64.b64encode(image_data).decode("utf-8")
        
        try:
            extraction_response = client.chat.completions.create(
                model="information-extract",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:application/octet-stream;base64,{image_b64}"}
                            }
                        ]
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": diagnosis_schema
                }
            )
            
            if not extraction_response.choices or not extraction_response.choices[0].message.content:
                raise HTTPException(status_code=500, detail="API 응답이 비어있습니다.")
                
            fields = extraction_response.choices[0].message.content
            parsed = json.loads(fields)
            
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"API 응답 JSON 파싱 실패: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upstage API 호출 실패: {str(e)}")

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
                
        # diagnosis_text 정리 (줄바꿈 제거 및 깔끔하게 정리)
        if "diagnosis_text" in parsed:
            diagnosis_text = parsed["diagnosis_text"]
            # 줄바꿈 제거
            diagnosis_text = diagnosis_text.replace('\n', ' ')
            # 여러 공백을 하나로
            diagnosis_text = re.sub(r'\s+', ' ', diagnosis_text)
            # 앞뒤 공백 제거
            diagnosis_text = diagnosis_text.strip()
            
            parsed["diagnosis_text"] = diagnosis_text
        for key, value in parsed.items():
            if hasattr(diagnosis, key):
                setattr(diagnosis, key, value)
        db.commit()
        db.refresh(diagnosis)
        return {
            "message": "진단서 OCR 처리 완료",
            "diagnosis_id": diagnosis_id,
            "data": parsed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 실패: {str(e)}")

@router.patch("/receipts/ocr/{receipt_id}",
    summary="영수증 OCR 처리",
    description="AI를 사용하여 영수증 이미지에서 텍스트를 추출하고 의료비 정보를 자동으로 인식하여 데이터베이스에 저장합니다.",
    response_description="OCR 처리 완료 메시지")
async def ocr_receipt(receipt_id: int, db: Session = Depends(get_db)):
    try:
        receipt = db.query(MedicalReceipt).filter(
            MedicalReceipt.id == receipt_id,
            MedicalReceipt.is_deleted == False
        ).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다.")
        if not receipt.image_url:
            raise HTTPException(status_code=400, detail="영수증 이미지가 업로드되지 않았습니다.")
        # 스토리지 서비스를 사용하여 파일 읽기
        try:
            if receipt.image_url.startswith('http'):
                # S3 URL인 경우
                response = requests.get(receipt.image_url)
                response.raise_for_status()
                image_data = response.content
            else:
                # 로컬 파일인 경우
                file_path = os.path.join(UPLOAD_DIR, "receipts", os.path.basename(receipt.image_url))
                if not os.path.exists(file_path):
                    raise HTTPException(status_code=404, detail="이미지 파일이 존재하지 않습니다.")
                with open(file_path, 'rb') as f:
                    image_data = f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"이미지 파일 읽기 실패: {str(e)}")
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        try:
            extraction_response = client.chat.completions.create(
                model="information-extract",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:application/octet-stream;base64,{image_b64}"}
                            }
                        ]
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": receipt_schema
                }
            )
            
            if not extraction_response.choices or not extraction_response.choices[0].message.content:
                raise HTTPException(status_code=500, detail="API 응답이 비어있습니다.")
                
            fields = extraction_response.choices[0].message.content
            parsed = json.loads(fields)
            
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"API 응답 JSON 파싱 실패: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upstage API 호출 실패: {str(e)}")

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
                
        # treatment_details 정리 (줄바꿈 제거 및 깔끔하게 정리)
        if "treatment_details" in parsed:
            treatment_text = parsed["treatment_details"]
            # 줄바꿈 제거
            treatment_text = treatment_text.replace('\n', ' ')
            # 여러 공백을 하나로
            treatment_text = re.sub(r'\s+', ' ', treatment_text)
            # 금액 정보 제거 (숫자+콤마 패턴)
            treatment_text = re.sub(r'\d{1,3}(?:,\d{3})*', '', treatment_text)
            # 불필요한 특수문자 제거
            treatment_text = re.sub(r'[^\w\s가-힣,]', '', treatment_text)
            # 여러 쉼표를 하나로
            treatment_text = re.sub(r',+', ',', treatment_text)
            # 앞뒤 공백 제거
            treatment_text = treatment_text.strip()
            # 앞뒤 쉼표 제거
            treatment_text = treatment_text.strip(',')
            
            parsed["treatment_details"] = treatment_text
        for key, value in parsed.items():
            if hasattr(receipt, key):
                setattr(receipt, key, value)
        db.commit()
        db.refresh(receipt)
        return {
            "message": "영수증 OCR 처리 완료",
            "receipt_id": receipt_id,
            "data": parsed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 실패: {str(e)}")

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