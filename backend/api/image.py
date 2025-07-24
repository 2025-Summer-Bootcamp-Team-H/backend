from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import MedicalDiagnosis, MedicalReceipt
from fastapi.responses import RedirectResponse, FileResponse
import os

router = APIRouter()

@router.get("/images/diagnosis/{diagnosis_id}", summary="진단서 이미지 반환")
async def get_diagnosis_image(diagnosis_id: int, db: Session = Depends(get_db)):
    diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == diagnosis_id).first()
    if not diagnosis or not diagnosis.image_url:
        raise HTTPException(status_code=404, detail="진단서 이미지가 없습니다.")
    # 클라우드 스토리지 URL이면 리다이렉트
    if diagnosis.image_url.startswith("http"):
        response = RedirectResponse(diagnosis.image_url)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    # 로컬 파일이면 파일 반환
    local_path = diagnosis.image_url
    if not os.path.isabs(local_path):
        # 상대경로면 uploads/diagnosis/ 등으로 보정
        local_path = os.path.join("uploads", "diagnosis", os.path.basename(local_path))
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="로컬 이미지 파일이 없습니다.")
    return FileResponse(local_path)

@router.get("/images/receipt/{receipt_id}", summary="영수증 이미지 반환")
async def get_receipt_image(receipt_id: int, db: Session = Depends(get_db)):
    receipt = db.query(MedicalReceipt).filter(MedicalReceipt.id == receipt_id).first()
    if not receipt or not receipt.image_url:
        raise HTTPException(status_code=404, detail="영수증 이미지가 없습니다.")
    if receipt.image_url.startswith("http"):
        return RedirectResponse(receipt.image_url)
    local_path = receipt.image_url
    if not os.path.isabs(local_path):
        local_path = os.path.join("uploads", "receipts", os.path.basename(local_path))
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="로컬 이미지 파일이 없습니다.")
    return FileResponse(local_path) 