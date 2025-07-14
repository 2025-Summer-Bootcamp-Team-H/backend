from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Claim, ClaimCalculation, MedicalDiagnosis, MedicalReceipt, User, UserContract, InsuranceProduct, InsuranceClause
from models.schemas import ClaimCreate
from typing import Optional
from pydantic import BaseModel
from services.claim_calculator import ClaimCalculator
import json
from datetime import datetime

router = APIRouter()

class ClaimCreateRequest(BaseModel):
    diagnosis_id: int
    receipt_id: int

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
        
        # 환자의 가입 보험 조회
        contract = db.query(UserContract).filter(
            UserContract.patient_name == diagnosis.patient_name,
            UserContract.patient_ssn == diagnosis.patient_ssn
        ).first()
        
        if not contract:
            raise HTTPException(status_code=404, detail="해당 환자의 가입 보험을 찾을 수 없습니다")
        
        # 보험상품 조회
        product = db.query(InsuranceProduct).filter(InsuranceProduct.id == contract.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="보험상품을 찾을 수 없습니다")
        
        # Claim 테이블에 저장
        claim = Claim(
            user_id=default_user_id,
            patient_name=diagnosis.patient_name,
            patient_ssn=diagnosis.patient_ssn,
            diagnosis_id=diagnosis.id,
            receipt_id=receipt.id,
            claim_amount=0,  # 초기값, 계산 후 업데이트
            claim_reason="",  # 계산 후 상세내역으로 업데이트
            status="pending",
            created_at=datetime.now()
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)
        
        # 보험금 계산 (claim_calculator.py 활용)
        calculator = ClaimCalculator(db)
        
        # 해당 보험상품의 특약들 조회
        clauses = db.query(InsuranceClause).filter(
            InsuranceClause.product_id == contract.product_id,
            InsuranceClause.is_deleted == False
        ).all()
        
        # 보험금 계산 실행 - calculate_claim_with_clauses 메서드 사용
        calculation_result = calculator.calculate_claim_with_clauses(claim.id, clauses)
        
        # 계산 결과를 claim_reason에 JSON 형태로 저장
        detailed_info = {
            "applied_clauses": [
                {
                    "clause_name": calc["clause_name"],
                    "category": calc["category"],
                    "amount": calc["calculated_amount"],
                    "calculation_logic": calc["calculation_logic"]
                }
                for calc in calculation_result["calculations"]
            ],
            "calculation_basis": f"총 {len(calculation_result['calculations'])}개 특약 적용, 총 보험금 {calculation_result['total_amount']:,}원",
            "total_amount": calculation_result["total_amount"]
        }
        
        # claim_reason 업데이트
        claim.claim_reason = f"상세내역: {json.dumps(detailed_info, ensure_ascii=False)}"
        claim.claim_amount = calculation_result["total_amount"]
        
        # 청구 상태 설정 (보험금이 있으면 approved, 없으면 rejected)
        if calculation_result["total_amount"] > 0:
            claim.status = "approved"
        else:
            claim.status = "rejected"
        
        db.commit()
        
        return {
            "message": "청구 생성 완료",
            "claim_id": claim.id,
            "user_id": default_user_id,
            "user_name": default_user.name,
            "user_email": default_user.email,
            "patient_name": diagnosis.patient_name,
            "diagnosis_name": diagnosis.diagnosis_name,
            "insurance_product": product.name,
            "claim_amount": calculation_result["total_amount"],
            "status": claim.status,
            "applied_clauses": len(calculation_result["calculations"]),
            "detailed_info": detailed_info
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"청구 생성 실패: {str(e)}")

@router.get("/claims", summary="청구 목록 조회", description="모든 청구목록 반환 (이름, 진단명, 보험금, 신청일, 담당자, 상태)")
async def get_claims(db: Session = Depends(get_db)):
    # All claims (passed + failed)
    claims = db.query(Claim).all()
    results = []
    for claim in claims:
        # 진단명 조인
        diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == claim.diagnosis_id).first()
        diagnosis_name = diagnosis.diagnosis_name if diagnosis else None
        # 담당자명 조인
        user = db.query(User).filter(User.id == claim.user_id).first()
        user_name = user.name if user else None
        results.append({
            "claim_id": claim.id,
            "patient_name": claim.patient_name,
            "diagnosis_name": diagnosis_name,
            "claim_amount": claim.claim_amount,
            "created_at": claim.created_at,
            "user_name": user_name,
            "status": claim.status
        })
    return results 

@router.get("/claims/{claim_id}", summary="청구 상세정보 조회", description="요약된 청구 상세정보 조회")
async def get_claim_details(claim_id: int, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다")

    # 진단서, 계약, 보험상품 조인
    diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == claim.diagnosis_id).first()
    contract = db.query(UserContract).filter(
        UserContract.patient_name == claim.patient_name,
        UserContract.patient_ssn == claim.patient_ssn
    ).first()
    product_id = contract.product_id if contract else None
    product_name = None
    if contract:
        product = db.query(InsuranceProduct).filter(InsuranceProduct.id == contract.product_id).first()
        if product:
            product_name = product.name

    # 주민번호에서 생년월일 파싱
    birth_date = None
    if claim.patient_ssn and len(claim.patient_ssn) >= 6:
        y, m, d = claim.patient_ssn[:2], claim.patient_ssn[2:4], claim.patient_ssn[4:6]
        # 2000년대 이후/이전 구분(간단히 00~21은 2000년대, 그 외 1900년대)
        century = "19" if int(y) > 21 else "20"
        birth_date = f"{century}{y}-{m}-{d}"

    # 심사 통과 여부
    review_status = "passed" if claim.claim_amount > 0 else "failed"

    # 상세내역 파싱
    detailed_info = {}
    if "상세내역:" in claim.claim_reason:
        try:
            json_start = claim.claim_reason.find("상세내역: ") + len("상세내역: ")
            json_part = claim.claim_reason[json_start:]
            detailed_info = json.loads(json_part)
        except:
            detailed_info = {}

    # 특약 내용 (description 조인)
    clauses = []
    if detailed_info.get("applied_clauses"):
        for c in detailed_info["applied_clauses"]:
            clause_name = c.get("clause_name")
            clause_obj = None
            if product_id:
                clause_obj = db.query(InsuranceClause).filter(InsuranceClause.clause_name == clause_name, InsuranceClause.product_id == product_id).first()
            if not clause_obj:
                clause_obj = db.query(InsuranceClause).filter(InsuranceClause.clause_name == clause_name).first()
            clauses.append({
                "clause_name": clause_name,
                "description": clause_obj.description if clause_obj else None,
                "calculated_amount": c.get("amount")
            })
    # 심사 근거 및 조항 해석
    review_basis = detailed_info.get("calculation_basis")
    if not review_basis:
        review_basis = claim.claim_reason

    # 보험상품명 보완: 계약이 없을 때는 매칭된 특약의 product_id로 상품명 조인
    if not product_name:
        # applied_clauses에서 첫 번째 특약의 product_id로 상품명 조인
        first_clause_obj = None
        if clauses:
            clause_name = clauses[0]["clause_name"]
            clause_obj = db.query(InsuranceClause).filter(InsuranceClause.clause_name == clause_name).first()
            if clause_obj:
                product = db.query(InsuranceProduct).filter(InsuranceProduct.id == clause_obj.product_id).first()
                if product:
                    product_name = product.name

    return {
        "patient_name": claim.patient_name,
        "patient_ssn": claim.patient_ssn,
        "review_status": review_status,
        "insurance_product": product_name,
        "claim_amount": claim.claim_amount,
        "clauses": clauses,
        "review_basis": review_basis
    } 