import os
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from services.storage_service import storage_service

router = APIRouter()

# 환경변수에서 업로드 디렉토리 설정
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
DIAGNOSIS_DIR = os.path.join(UPLOAD_DIR, "diagnosis")
RECEIPT_DIR = os.path.join(UPLOAD_DIR, "receipts")

# 디렉토리 생성 (로컬 스토리지용)
os.makedirs(DIAGNOSIS_DIR, exist_ok=True)
os.makedirs(RECEIPT_DIR, exist_ok=True)

@router.post(
    "/diagnoses/images",
    summary="진단서 이미지 업로드",
    description="진단서 이미지 파일을 업로드하고 기본 진단서 레코드를 생성합니다. 나머지 필드는 추후 업데이트될 수 있습니다.",
    response_description="업로드 성공 시 생성된 진단서 ID 반환"
)
async def upload_diagnosis(
    file: UploadFile = File(..., description="진단서 이미지 파일"),
    db: Session = Depends(get_db)
):
    try:
        ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일 이름이 없습니다.")
        ext = file.filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다.")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"diagnosis_{timestamp}.{ext}"
        
        # 스토리지 서비스를 사용하여 파일 업로드
        file_url = await storage_service.upload_file(file, "diagnosis", filename)

        diagnosis = MedicalDiagnosis(
            user_id=1,
            patient_name="",
            patient_ssn="",
            diagnosis_name="",
            diagnosis_date= datetime.now().date(),
            diagnosis_text="",
            hospital_name="",
            doctor_name="",
            icd_code="",
            admission_days=0,
            image_url = file_url  # 스토리지 서비스에서 반환된 URL 사용
        )
        db.add(diagnosis)
        db.commit()
        db.refresh(diagnosis)

        return {"message": "진단서 업로드 성공", "diagnosis_id": diagnosis.id, "file_url": file_url}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")

@router.post(
    "/receipts/images",
    summary="영수증 이미지 업로드",
    description="영수증 이미지 파일을 업로드하고 기본 영수증 레코드를 생성합니다. 나머지 필드는 추후 업데이트될 수 있습니다.",
    response_description="업로드 성공 시 생성된 영수증 ID 반환"
)
async def upload_receipt(
    file: UploadFile = File(..., description="영수증 이미지 파일"),
    db: Session = Depends(get_db)
):
    try:
        ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일 이름이 없습니다.")
        ext = file.filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다.")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"receipt_{timestamp}.{ext}"
        
        # 스토리지 서비스를 사용하여 파일 업로드
        file_url = await storage_service.upload_file(file, "receipts", filename)

        receipt = MedicalReceipt(
            user_id=1,
            patient_name="",
            receipt_date= datetime.now().date(),
            total_amount=0,
            hospital_name="",
            treatment_details="",
            image_url = file_url  # 스토리지 서비스에서 반환된 URL 사용
        )

        db.add(receipt)
        db.commit()
        db.refresh(receipt)

        return {"message": "영수증 업로드 성공", "receipt_id": receipt.id, "file_url": file_url}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")

