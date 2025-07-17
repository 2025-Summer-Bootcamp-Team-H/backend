from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.schemas import ForgeryRequest
from models.models import MedicalDiagnosis, MedicalReceipt, ForgeryAnalysis
from services.forgery_service import analyze_forgery_from_local_path
from models.database import get_db

router = APIRouter()

@router.post(
    "/forgery_analysis",
    summary="위조분석 실행",
    description="진단서와 영수증을 위조분석합니다."
)
def analyze_forgery(data: ForgeryRequest, db: Session = Depends(get_db)):
    # 진단서, 영수증 존재 확인
    diagnosis = db.query(MedicalDiagnosis).filter_by(id=data.diagnosis_id).first()
    if not diagnosis or not getattr(diagnosis, "image_url", None):
        raise HTTPException(status_code=404, detail="Diagnosis not found or no image_url")
    receipt = db.query(MedicalReceipt).filter_by(id=data.receipt_id).first()
    if not receipt or not getattr(receipt, "image_url", None):
        raise HTTPException(status_code=404, detail="Receipt not found or no image_url")

    # 각각 위조분석
    diagnosis_result = analyze_forgery_from_local_path(diagnosis.image_url)  # type: ignore
    receipt_result = analyze_forgery_from_local_path(receipt.image_url)      # type: ignore

    # 결과 저장
    forgery = ForgeryAnalysis(
        diagnosis_id=data.diagnosis_id,
        receipt_id=data.receipt_id,
        analysis_result=f"diagnosis: {diagnosis_result['predicted_class']}, receipt: {receipt_result['predicted_class']}",
        confidence_score=(diagnosis_result['confidence'] + receipt_result['confidence']) / 2,
        fraud_indicators=None
    )
    db.add(forgery)
    db.commit()
    db.refresh(forgery)

    return {
        "forgery_analysis_id": forgery.id,
        "diagnosis_result": diagnosis_result,
        "receipt_result": receipt_result
    }

@router.get(
    "/forgery_analysis/{forgery_analysis_id}",
    summary="위조분석 결과 조회",
    description="위조분석 결과를 조회합니다."
)
def get_forgery_analysis(forgery_analysis_id: int, db: Session = Depends(get_db)):
    forgery = db.query(ForgeryAnalysis).filter_by(id=forgery_analysis_id).first()
    if not forgery:
        raise HTTPException(status_code=404, detail="Forgery analysis not found")
    return forgery
