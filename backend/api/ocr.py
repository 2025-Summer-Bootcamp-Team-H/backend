from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from openai import OpenAI
import os
from urllib.parse import urlparse
import json
import base64
import re

router = APIRouter()

# OpenAI API 키 환경변수에서 불러오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# 컨테이너 내부 기준 업로드 디렉토리
UPLOAD_DIR = "/app/uploads"

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

@router.patch("/diagnoses/ocr/{diagnosis_id}",
    summary="진단서 OCR 처리",
    description="AI를 사용하여 진단서 이미지에서 텍스트를 추출하고 진단 정보를 자동으로 인식하여 데이터베이스에 저장합니다.",
    response_description="OCR 처리 완료 메시지")
async def ocr_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    """
    진단서 OCR 실행 후 정보 추출 및 저장
    """
    try:
        # 1. 진단서 조회
        diagnosis = db.query(MedicalDiagnosis).filter(
            MedicalDiagnosis.id == diagnosis_id,
            MedicalDiagnosis.is_deleted == False
        ).first()
        
        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다.")

        # 2. 이미지 파일 경로
         Feat/18-monitoring

        if not diagnosis.image_url:
          main
            raise HTTPException(status_code=400, detail="진단서 이미지가 업로드되지 않았습니다.")
            
        filename = os.path.basename(urlparse(str(diagnosis.image_url)).path)
        file_path = os.path.join(UPLOAD_DIR, "diagnosis", filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="이미지 파일이 존재하지 않습니다.")

        # 3. 이미지 base64 인코딩 및 GPT 호출
        with open(file_path, "rb") as image_file:
            image_bytes = image_file.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 의료 진단서 OCR 전문 AI입니다. 정확하고 신뢰할 수 있는 정보만 추출해주세요."},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "이 진단서 이미지에서 다음 항목을 추출해줘:\n"
                                "1. 환자 이름 (한글 정확히 인식)\n"
                                "2. 주민등록번호 (하이픈 포함)\n"
                                "3. 진단명\n"
                                "4. 진단일자 (YYYY-MM-DD 형식)\n"
                                "5. 진단 내용 요약 (의학적 용어 사용)\n"
                                "6. 병원명\n"
                                "7. 의사 이름\n"
                                "8. ICD 코드 (있는 경우)\n"
                                "9. 입원 일수 (외래인 경우 0)\n"
                                "JSON 형식으로 반환해줘. 키 이름은 영어로:\n"
                                "`patient_name`, `patient_ssn`, `diagnosis_name`, `diagnosis_date`, `diagnosis_text`, `hospital_name`, `doctor_name`, `icd_code`, `admission_days`"
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        # 4. 응답 파싱
        result_text = response.choices[0].message.content
        if result_text is None:
            raise HTTPException(status_code=500, detail="AI 응답이 비어 있습니다.")

        result_text = result_text.strip()

        # ```json ... ``` 제거
        cleaned_text = re.sub(r"```json\s*([\s\S]*?)```", r"\1", result_text, flags=re.MULTILINE)
        if not cleaned_text:
            raise HTTPException(status_code=500, detail="OCR 결과에 JSON 형식이 없습니다.")

        parsed = json.loads(cleaned_text)

        # 5. 날짜 처리
        if parsed.get("diagnosis_date"):
            try:
                parsed["diagnosis_date"] = datetime.strptime(parsed["diagnosis_date"], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")

        # 6. admission_days: null → 0
        if "admission_days" in parsed:
            if parsed["admission_days"] in [None, "", "null"]:
                parsed["admission_days"] = 0
            else:
                try:
                    parsed["admission_days"] = int(parsed["admission_days"])
                except (ValueError, TypeError):
                    parsed["admission_days"] = 0

        # 7. DB 필드 업데이트
        for key, value in parsed.items():
            if hasattr(diagnosis, key):  # 안전한 필드 업데이트
                setattr(diagnosis, key, value)

        db.commit()
        db.refresh(diagnosis)

        return {
            "message": "진단서 OCR 처리 완료",
            "diagnosis_id": diagnosis_id,
            "data": parsed
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="OCR 결과 파싱에 실패했습니다. AI 응답을 확인해주세요.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 실패: {str(e)}")

@router.patch("/receipts/ocr/{receipt_id}",
    summary="영수증 OCR 처리",
    description="AI를 사용하여 영수증 이미지에서 텍스트를 추출하고 의료비 정보를 자동으로 인식하여 데이터베이스에 저장합니다.",
    response_description="OCR 처리 완료 메시지")
async def ocr_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """
    영수증 OCR 실행 후 정보 추출 및 저장
    """
    try:
        # 1. DB에서 영수증 조회
        receipt = db.query(MedicalReceipt).filter(
            MedicalReceipt.id == receipt_id,
            MedicalReceipt.is_deleted == False
        ).first()
        
        if not receipt:
            raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다.")

        # 2. 이미지 파일 경로 파싱
        Feat/18-monitoring
        if not receipt.image_url:
        main
            raise HTTPException(status_code=400, detail="영수증 이미지가 업로드되지 않았습니다.")
            
        filename = os.path.basename(urlparse(str(receipt.image_url)).path)
        file_path = os.path.join(UPLOAD_DIR, "receipts", filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="이미지 파일이 존재하지 않습니다.")

        # 3. 이미지 base64 인코딩
        with open(file_path, "rb") as image_file:
            image_bytes = image_file.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # 4. GPT Vision API 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 의료 영수증 OCR 전문 AI입니다. 정확한 금액과 정보를 추출해주세요."},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "이 의료 영수증에서 다음 항목들을 추출해줘:\n"
                                "1. 환자 이름 (한글 정확히 인식)\n"
                                "2. 병원명\n"
                                "3. 진료일자 (YYYY-MM-DD 형식)\n"
                                "4. 총 진료비 (숫자만)\n"
                                "5. 진료 상세내역 (간단한 요약)\n\n"
                                "결과는 다음 키 이름으로 JSON 형식으로 반환해줘:\n"
                                "`patient_name`, `hospital_name`, `receipt_date`, `total_amount`, `treatment_details`"
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        # 5. 응답 파싱
        if not response or not response.choices or not response.choices[0].message.content:
            raise HTTPException(status_code=500, detail="AI 응답이 비어 있습니다.")

        result_text = response.choices[0].message.content.strip()

        # ```json ... ``` 제거
        cleaned_text = re.sub(r"```json\s*([\s\S]*?)```", r"\1", result_text, flags=re.MULTILINE).strip()

        parsed = json.loads(cleaned_text)

        # 6. 날짜 처리
        if parsed.get("receipt_date"):
            try:
                parsed["receipt_date"] = datetime.strptime(parsed["receipt_date"], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다.")

        # 7. 총 금액 처리
        if "total_amount" in parsed:
            try:
                parsed["total_amount"] = float(parsed["total_amount"])
            except:
                parsed["total_amount"] = 0.0

        # 8. DB 업데이트
        for key, value in parsed.items():
            if hasattr(receipt, key):  # 안전한 필드 업데이트
                setattr(receipt, key, value)

        db.commit()
        db.refresh(receipt)

        return {
            "message": "영수증 OCR 처리 완료",
            "receipt_id": receipt_id,
            "data": parsed
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="OCR 결과 파싱에 실패했습니다. AI 응답을 확인해주세요.")
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