from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Claim, ClaimCalculation, MedicalDiagnosis, MedicalReceipt
from typing import Optional, List

router = APIRouter()

@router.get("/claims",
    summary="청구 전체 목록 조회",
    description="모든 보험금 청구 목록을 조회합니다. 청구 ID, 환자명, 청구 금액, 상태, 신청일 등 기본 정보와 함께 claim_calculations 테이블과 조인하여 계산 정보도 포함합니다.",
    response_description="청구 목록")
async def get_all_claims(db: Session = Depends(get_db)):
    """
    청구 전체 목록 조회
    - pk, 직원id, 환자이름, 주민번호, 진단서pk, 영수증pk, 청구 보험금, 청구 사유, 청구 상태, 청구 신청일 등
    - claim_calculations 테이블과 조인하여 계산 정보도 포함
    """
    try:
        # TODO: Claim 테이블 조회
        # TODO: ClaimCalculation 테이블과 조인
        # TODO: 관련 정보 포함하여 반환
        
        return {
            "claims": [
                {
                    "id": 1,
                    "user_id": 1,
                    "patient_name": "홍길동",
                    "patient_ssn": "123456-1234567",
                    "diagnosis_id": 1,
                    "receipt_id": 1,
                    "claim_amount": 1500000,
                    "claim_reason": "의료비 청구",
                    "status": "pending",
                    "created_at": "2024-01-15T10:30:00"
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"청구 목록 조회 실패: {str(e)}")

@router.get("/claims/{claim_id}",
    summary="청구 상세 조회",
    description="특정 청구의 상세 정보를 조회합니다. 청구 정보와 함께 계산 과정, 진단서, 영수증 정보를 포함합니다.",
    response_description="청구 상세 정보")
async def get_claim_detail(claim_id: int, db: Session = Depends(get_db)):
    """
    청구 상세 조회
    - 청구 정보와 함께 계산 과정, 진단서, 영수증 정보 포함
    """
    try:
        # TODO: Claim 상세 조회
        # TODO: 관련 테이블 조인
        # TODO: 계산 과정 포함하여 반환
        
        return {
            "claim_id": claim_id,
            "patient_name": "홍길동",
            "diagnosis": {"id": 1, "diagnosis_name": "감기"},
            "receipt": {"id": 1, "total_amount": 1500000},
            "calculations": [
                {"clause_id": 1, "calculated_amount": 500000}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"청구 상세 조회 실패: {str(e)}")


@router.get("/claims/search",
    summary="청구 검색",
    description="환자명이나 청구 상태로 청구를 검색합니다.",
    response_description="검색 결과")
async def search_claims(
    patient_name: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    환자명으로 청구 검색
    """
    try:
        query = db.query(Claim)
        
        if patient_name:
            query = query.filter(Claim.patient_name.contains(patient_name))
        if status:
            query = query.filter(Claim.status == status)
        
        claims = query.all()
        
        return {
            "claims": [
                {
                    "id": claim.id,
                    "patient_name": claim.patient_name,
                    "claim_amount": claim.claim_amount,
                    "status": claim.status,
                    "created_at": claim.created_at.isoformat() if claim.created_at else None
                }
                for claim in claims
            ],
            "total_count": len(claims)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}") 