from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.schemas import ForgeryRequest
from models.models import MedicalDiagnosis, MedicalReceipt, ForgeryAnalysis
from services.forgery_service import analyze_forgery_from_local_path
from models.database import get_db
import requests
import os
import tempfile
from services.storage_service import storage_service

router = APIRouter()

def download_file_to_temp(file_url: str) -> str:
    """파일을 임시 디렉토리에 다운로드하여 로컬 경로 반환"""
    try:
        if file_url.startswith('http'):
            # S3 URL인 경우 다운로드
            response = requests.get(file_url)
            response.raise_for_status()
            
            # 임시 파일 생성
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_url)[1])
            temp_file.write(response.content)
            temp_file.close()
            return temp_file.name
        else:
            # 로컬 파일인 경우 경로 반환
            return os.path.join("./uploads", file_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 다운로드 실패: {str(e)}")

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

    try:
        # 파일을 임시 디렉토리에 다운로드
        diagnosis_temp_path = download_file_to_temp(diagnosis.image_url)
        receipt_temp_path = download_file_to_temp(receipt.image_url)

        # 각각 위조분석
        diagnosis_result = analyze_forgery_from_local_path(diagnosis_temp_path)
        receipt_result = analyze_forgery_from_local_path(receipt_temp_path)

        # 임시 파일 정리
        if diagnosis_temp_path.startswith('/tmp'):
            os.unlink(diagnosis_temp_path)
        if receipt_temp_path.startswith('/tmp'):
            os.unlink(receipt_temp_path)

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
    except Exception as e:
        # 임시 파일 정리
        if 'diagnosis_temp_path' in locals() and diagnosis_temp_path.startswith('/tmp'):
            try:
                os.unlink(diagnosis_temp_path)
            except:
                pass
        if 'receipt_temp_path' in locals() and receipt_temp_path.startswith('/tmp'):
            try:
                os.unlink(receipt_temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"위조분석 실패: {str(e)}")

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
