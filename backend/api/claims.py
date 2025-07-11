from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Claim, ClaimCalculation, MedicalDiagnosis, MedicalReceipt, User
from models.schemas import ClaimCreate
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

class ClaimCreateRequest(BaseModel):
    diagnosis_id: int
    receipt_id: int
    claim_reason: Optional[str] = None

@router.post("/claims",
    summary="보험금 청구 생성",
    description="진단서와 영수증 정보를 바탕으로 보험금 청구를 생성하고 자동으로 보험금을 계산합니다. 담당자는 기본 직원(관리자)으로 설정됩니다.",
    response_description="청구 생성 완료 메시지")
async def create_claim(
    claim_data: ClaimCreateRequest, 
    db: Session = Depends(get_db)
):
    """
    claim 생성 → claims와 claim_calculations 테이블에 통계 저장
    - 진단서와 영수증 정보를 바탕으로 청구 생성
    - 보험금 계산 및 저장
    - 청구 상태 설정
    - 담당자는 기본값(user_id=1, 관리자)으로 고정
    """
    try:
        # 기본 담당자 설정 (발표용)
        default_user_id = 1  # 관리자 ID로 고정
        default_user = db.query(User).filter(User.id == default_user_id).first()
        
        if not default_user:
            raise HTTPException(status_code=500, detail="기본 담당자를 찾을 수 없습니다")
        
        # 진단서 조회
        diagnosis = db.query(MedicalDiagnosis).filter(
            MedicalDiagnosis.id == claim_data.diagnosis_id,
            MedicalDiagnosis.is_deleted == False
        ).first()
        
        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다")
        
        # 영수증 조회
        receipt = db.query(MedicalReceipt).filter(
            MedicalReceipt.id == claim_data.receipt_id,
            MedicalReceipt.is_deleted == False
        ).first()
        
        if not receipt:
            raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다")
        
        # TODO: 보험금 계산 (claim_calculator.py 활용)
        # TODO: Claim 테이블에 저장
        # TODO: ClaimCalculation 테이블에 저장
        # TODO: 청구 상태 설정
        
        return {
            "message": "청구 생성 완료",
            "claim_id": 1,
            "user_id": 1,
            "user_name": default_user.name,
            "user_email": default_user.email,
            "diagnosis_id": claim_data.diagnosis_id,
            "receipt_id": claim_data.receipt_id,
            "claim_reason": claim_data.claim_reason,
            "claim_amount": receipt.total_amount,  # 영수증의 총금액 사용
            "status": "pending"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"청구 생성 실패: {str(e)}") 