import os
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt

router = APIRouter()

UPLOAD_DIR = "./uploads"
DIAGNOSIS_DIR = os.path.join(UPLOAD_DIR, "diagnosis")
RECEIPT_DIR = os.path.join(UPLOAD_DIR, "receipts")

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
        ALLOWED_EXTENSIONS = {"jpg"}
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일 이름이 없습니다.")
        ext = file.filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다.")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"diagnosis_{timestamp}.{ext}"
        diagnosis_dir = DIAGNOSIS_DIR
        #diagnosis_dir = os.path.join(UPLOAD_DIR, "diagnosis")
        os.makedirs(diagnosis_dir, exist_ok=True)
        file_path = os.path.join(diagnosis_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

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
            image_url=f"/{file_path.replace(os.sep, '/')}"  # 경로 슬래시 통일
        )
        db.add(diagnosis)
        db.commit()
        db.refresh(diagnosis)

        return {"message": "진단서 업로드 성공", "diagnosis_id": diagnosis.id}

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
        ALLOWED_EXTENSIONS = {"jpg"}
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일 이름이 없습니다.")
        ext = file.filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다.")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"receipt_{timestamp}.{ext}"
        receipt_dir = RECEIPT_DIR
        #receipt_dir = os.path.join(UPLOAD_DIR, "receipts")
        os.makedirs(receipt_dir, exist_ok=True)
        file_path = os.path.join(receipt_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)


        receipt = MedicalReceipt(
            user_id=1,
            patient_name="",
            receipt_date= datetime.now().date(),
            total_amount=0,
            hospital_name="",
            treatment_details="",
            image_url=f"/{file_path.replace(os.sep, '/')}"
        )

        db.add(receipt)
        db.commit()
        db.refresh(receipt)

        return {"message": "영수증 업로드 성공", "receipt_id": receipt.id}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")

