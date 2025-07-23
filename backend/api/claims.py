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
from collections import Counter, defaultdict
from datetime import date
from utils.auth import get_current_user

router = APIRouter()

class ClaimCreateRequest(BaseModel):
    diagnosis_id: int
    receipt_id: int


class BulkDeleteRequest(BaseModel):
    claim_ids: list[int]


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
        
        # 청구 상태 설정 (보험금이 있으면 passed, 없으면 failed)
        if calculation_result["total_amount"] > 0:
            claim.status = "passed"
        else:
            claim.status = "failed"
        
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

@router.get("/claims",
    summary="보험금 청구 전체 목록 조회",
    description="모든 보험금 청구 목록을 조회합니다.",
    response_description="청구 목록",
    dependencies=[Depends(get_current_user)]
)
async def get_claims(db: Session = Depends(get_db)):
    # All claims (passed + failed), 최신순 정렬
    claims = db.query(Claim).order_by(Claim.created_at.desc()).all()
    results = []
    for claim in claims:
        # 진단명 조인
        diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == claim.diagnosis_id).first()
        diagnosis_name = diagnosis.diagnosis_name if diagnosis else None
        # 담당자명 조인
        user = db.query(User).filter(User.id == claim.user_id).first()
        user_name = user.name if user else None
        # status 업데이트: claim_amount > 0이면 "passed", 0이면 "failed"
        if claim.claim_amount > 0:
            claim.status = "passed"
        else:
            claim.status = "failed"
        db.commit()
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

def mask_ssn(ssn: str) -> str:
    if ssn and len(ssn) >= 8:
        return ssn[:7] + "******"
    return ssn

@router.get("/claims/search",
    summary="청구 검색",
    description="환자명이나 청구 상태로 청구를 검색합니다.",
    response_description="검색 결과",
    dependencies=[Depends(get_current_user)]
)
async def search_claims_by_patient_name(
    patient_name: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Claim)
    if patient_name:
        query = query.filter(Claim.patient_name == patient_name)
    if status:
        query = query.filter(Claim.status == status)
    # 최신순 정렬 추가
    claims = query.order_by(Claim.created_at.desc()).all()
    results = []
    for claim in claims:
        diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == claim.diagnosis_id).first()
        diagnosis_name = diagnosis.diagnosis_name if diagnosis else None
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

@router.get("/claims/statistics/{claim_id}",
    summary="청구 상세 통계 조회",
    description="특정 청구의 통계 정보를 조회합니다.",
    response_description="청구 통계 정보",
    dependencies=[Depends(get_current_user)]
)
async def get_claim_statistics(claim_id: int, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다")
    patient_name = claim.patient_name
    patient_ssn = claim.patient_ssn
    patient_claims = db.query(Claim).filter(
        Claim.patient_name == patient_name,
        Claim.patient_ssn == patient_ssn
    ).order_by(Claim.created_at.desc()).all()
    claim_history = [
        {
            "claim_id": c.id,
            "diagnosis_name": db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == c.diagnosis_id).first().diagnosis_name if c.diagnosis_id else None,
            "claim_amount": c.claim_amount,
            "status": c.status,
            "created_at": c.created_at
        }
        for c in patient_claims
    ]
    status_counter = Counter(c.status for c in patient_claims)
    approval_stats = {
        "approved": status_counter.get("approved", 0),
        "rejected": status_counter.get("rejected", 0),
        "passed": status_counter.get("passed", 0),
        "failed": status_counter.get("failed", 0),
        "total": len(patient_claims)
    }
    diagnosis_trend = defaultdict(lambda: defaultdict(int))
    for c in patient_claims:
        diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == c.diagnosis_id).first()
        if diagnosis:
            month = c.created_at.strftime("%Y-%m")
            diagnosis_trend[diagnosis.diagnosis_name][month] += 1
    diagnosis_trend_list = [
        {"diagnosis_name": d, "monthly": dict(months)}
        for d, months in diagnosis_trend.items()
    ]
    patient_info = {
        "patient_name": patient_name,
        "patient_ssn": patient_ssn
    }
    return {
        "patient_info": patient_info,
        "claim_history": claim_history,
        "approval_stats": approval_stats,
        "diagnosis_trend": diagnosis_trend_list
    }

@router.get("/claims/{claim_id}",
    summary="청구 상세 조회",
    description="특정 청구의 상세 정보를 조회합니다.",
    response_description="청구 상세 정보",
    dependencies=[Depends(get_current_user)]
)
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


@router.delete("/claims/bulk",
    summary="선택된 청구들 일괄 삭제",
    description="체크박스로 선택된 청구들을 한 번에 삭제합니다.",
    response_description="일괄 삭제 결과",
    dependencies=[Depends(get_current_user)]
)
async def delete_selected_claims(
    delete_data: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    선택된 청구들을 일괄 삭제
    - 프론트엔드에서 체크박스로 선택한 청구 ID 리스트 받음
    - 각 청구와 관련된 ClaimCalculation 데이터도 함께 삭제
    """
    try:
        deleted_count = 0
        failed_count = 0
        failed_ids = []
        
        for claim_id in delete_data.claim_ids:
            try:
                # ClaimCalculation 먼저 삭제
                db.query(ClaimCalculation).filter(ClaimCalculation.claim_id == claim_id).delete()
                
                # Claim 삭제
                claim = db.query(Claim).filter(Claim.id == claim_id).first()
                if claim:
                    db.delete(claim)
                    deleted_count += 1
                else:
                    failed_count += 1
                    failed_ids.append(claim_id)
                    
            except Exception as e:
                failed_count += 1
                failed_ids.append(claim_id)
                continue
        
        db.commit()
        
        return {
            "message": f"일괄 삭제 완료: {deleted_count}개 성공, {failed_count}개 실패",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "failed_ids": failed_ids,
            "total_requested": len(delete_data.claim_ids)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"일괄 삭제 실패: {str(e)}")

@router.delete("/claims/{claim_id}",
    summary="개별 청구 삭제",
    description="특정 청구를 삭제합니다.",
    response_description="청구 삭제 결과",
    dependencies=[Depends(get_current_user)]
)
async def delete_claim(claim_id: int, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다")
    # 관련 ClaimCalculation 등도 함께 삭제(필요시)
    db.query(ClaimCalculation).filter(ClaimCalculation.claim_id == claim_id).delete()
    db.delete(claim)
    db.commit()
    return {"message": f"청구 {claim_id}가 삭제되었습니다."}

@router.delete("/claims",
    summary="전체 청구 삭제",
    description="모든 청구 데이터를 일괄 삭제합니다.",
    response_description="전체 청구 삭제 결과",
    dependencies=[Depends(get_current_user)]
)
async def delete_all_claims(db: Session = Depends(get_db)):
    # ClaimCalculation 등 종속 데이터 먼저 삭제
    db.query(ClaimCalculation).delete()
    db.query(Claim).delete()
    db.commit()
    return {"message": "모든 청구 데이터가 삭제되었습니다."} 