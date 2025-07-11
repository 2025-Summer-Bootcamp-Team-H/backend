from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from models.database import get_db
from models.models import Claim, User, MedicalDiagnosis, MedicalReceipt, InsuranceClause, UserSubscription, ClaimCalculation
from models.schemas import ClaimCreate, ClaimResponse

router = APIRouter(tags=["💰 보험금 청구"])

@router.post("/create", response_model=dict, summary="보험금 청구 생성 및 자동 심사", description="의료 진단서와 영수증을 기반으로 새로운 보험금 청구를 생성하고 자동으로 승인/불승인을 결정합니다.")
async def create_claim(
    claim: ClaimCreate,
    db: Session = Depends(get_db)
):
    """
    의료 진단서와 영수증을 기반으로 새로운 보험금 청구를 생성하고 자동 심사를 수행합니다.
    
    - **user_id**: 청구자 사용자 ID
    - **diagnosis_id**: 진단서 ID
    - **receipt_id**: 영수증 ID
    - **claim_reason**: 청구 사유 (선택사항)
    - **자동 심사**: 청구 생성 시 특약 가입 여부와 조건을 확인하여 자동으로 승인/불승인 결정
    - **보험금 계산**: 승인 시 각 특약별 보험금을 자동 계산하여 총 지급액 결정
    """
    try:
        # 사용자 존재 확인
        user = db.query(User).filter(User.id == claim.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 진단서 존재 확인
        diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == claim.diagnosis_id).first()
        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단서를 찾을 수 없습니다")
        
        # 영수증 존재 확인
        receipt = db.query(MedicalReceipt).filter(MedicalReceipt.id == claim.receipt_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다")
        
        # 진단서와 영수증의 환자 이름 일치 확인 (영수증에는 주민번호가 없음)
        if diagnosis.patient_name != receipt.patient_name:
            raise HTTPException(status_code=400, detail="진단서와 영수증의 환자 이름이 일치하지 않습니다")
        
        # 환자의 특약 가입 정보 조회
        subscriptions = db.query(UserSubscription).filter(
            UserSubscription.patient_ssn == diagnosis.patient_ssn,
            UserSubscription.status == 'active'
        ).all()
        
        if not subscriptions:
            # 가입한 특약이 없는 경우 -> 불승인
            new_claim = Claim(
                user_id=claim.user_id,
                patient_name=diagnosis.patient_name,
                patient_ssn=diagnosis.patient_ssn,
                diagnosis_id=claim.diagnosis_id,
                receipt_id=claim.receipt_id,
                claim_amount=0,  # 불승인이므로 0원
                claim_reason=f"{diagnosis.diagnosis_name} 진단에 따른 의료비 청구 [불승인 사유] 가입한 보험 특약이 없습니다.",
                status='rejected',
                created_at=datetime.utcnow()
            )
            
            db.add(new_claim)
            db.commit()
            db.refresh(new_claim)
            
            return {
                "message": "보험금 청구가 생성되었습니다 (자동 불승인)",
                "claim_id": new_claim.id,
                "user_id": new_claim.user_id,
                "patient_name": new_claim.patient_name,
                "patient_ssn": new_claim.patient_ssn,
                "original_claim_amount": receipt.total_amount,
                "approved_amount": 0,
                "status": "rejected",
                "rejection_reason": "가입한 보험 특약이 없습니다.",
                "created_at": new_claim.created_at.isoformat()
            }
        
        # 새 청구 생성 (일단 pending으로 생성 후 계산)
        new_claim = Claim(
            user_id=claim.user_id,
            patient_name=diagnosis.patient_name,
            patient_ssn=diagnosis.patient_ssn,
            diagnosis_id=claim.diagnosis_id,
            receipt_id=claim.receipt_id,
            claim_amount=receipt.total_amount,  # 일단 전체 금액으로 설정
            claim_reason=claim.claim_reason or f"{diagnosis.diagnosis_name} 진단에 따른 의료비 청구",
            status='pending',
            created_at=datetime.utcnow()
        )
        
        db.add(new_claim)
        db.commit()
        db.refresh(new_claim)
        
        # 각 특약별 보험금 계산
        total_approved_amount = 0
        calculation_results = []
        
        # 모든 특약 조회
        all_clauses = db.query(InsuranceClause).all()
        
        for subscription in subscriptions:
            # 특약 정보 조회
            clause = next((c for c in all_clauses if c.id == subscription.clause_id), None)
            if not clause:
                continue
                
            # 특약별 보험금 계산 로직
            calculated_amount = 0
            calculation_logic = ""
            
            # 실제 특약명을 기반으로 한 간단한 계산 로직
            clause_name = clause.clause_name.lower()
            treatment_cost = receipt.total_amount
            
            if "실손의료비" in clause.clause_name:
                # 실손의료비: 치료비의 80% 지급 (자기부담금 20%)
                calculated_amount = int(treatment_cost * 0.8)
                calculation_logic = f"실손의료비 특약: 치료비 {treatment_cost:,}원의 80% 지급"
                
            elif "수술비" in clause.clause_name or "골절" in clause.clause_name:
                # 수술비/골절 관련: 진단명에 따라 정액 지급
                if any(keyword in diagnosis.diagnosis_name for keyword in ["골절", "수술", "외과"]):
                    calculated_amount = 500000  # 50만원 정액 지급
                    calculation_logic = f"수술/골절 특약: {diagnosis.diagnosis_name} 진단에 대한 정액 지급"
                    
            elif "입원비" in clause.clause_name:
                # 입원비: 1일당 5만원 (최소 3일 이상 입원)
                # 여기서는 간단히 3일 입원으로 가정
                if treatment_cost >= 300000:  # 30만원 이상 치료비 = 입원으로 가정
                    calculated_amount = 150000  # 3일 * 5만원
                    calculation_logic = f"입원비 특약: 입원 3일 × 50,000원"
                    
            elif "암" in clause.clause_name:
                # 암 특약: 암 진단시 고액 지급
                if any(keyword in diagnosis.diagnosis_name for keyword in ["암", "종양", "악성"]):
                    calculated_amount = 10000000  # 1천만원
                    calculation_logic = f"암 특약: {diagnosis.diagnosis_name} 진단에 대한 정액 지급"
                    
            elif "응급의료비" in clause.clause_name:
                # 응급의료비: 응급실 이용시 치료비의 100% 지급
                if "응급" in diagnosis.hospital_name or treatment_cost >= 500000:
                    calculated_amount = treatment_cost
                    calculation_logic = f"응급의료비 특약: 응급 치료비 {treatment_cost:,}원 전액 지급"
            
            # 계산 결과 저장
            calculation = ClaimCalculation(
                claim_id=new_claim.id,
                clause_id=clause.id,
                calculated_amount=calculated_amount,
                calculation_logic=calculation_logic,
                created_at=datetime.utcnow()
            )
            
            db.add(calculation)
            calculation_results.append({
                "clause_name": clause.clause_name,
                "calculated_amount": calculated_amount,
                "logic": calculation_logic
            })
            
            if calculated_amount > 0:
                total_approved_amount += calculated_amount
        
        db.commit()
        
        # 최종 승인/불승인 결정 및 청구 정보 업데이트
        if total_approved_amount > 0:
            # 승인: 계산된 보험금이 있음
            new_claim.status = 'approved'
            new_claim.claim_amount = total_approved_amount
            status_message = "자동 승인"
        else:
            # 불승인: 계산된 보험금이 없음
            new_claim.status = 'rejected'
            new_claim.claim_amount = 0
            new_claim.claim_reason += " [불승인 사유] 가입한 특약의 보장 조건에 해당하지 않습니다."
            status_message = "자동 불승인"
        
        db.commit()
        db.refresh(new_claim)
        
        # 응답 생성
        response = {
            "message": f"보험금 청구가 생성되었습니다 ({status_message})",
            "claim_id": new_claim.id,
            "user_id": new_claim.user_id,
            "patient_name": new_claim.patient_name,
            "patient_ssn": new_claim.patient_ssn,
            "original_claim_amount": receipt.total_amount,
            "approved_amount": total_approved_amount,
            "status": new_claim.status,
            "status_korean": {
                "approved": "승인",
                "rejected": "불승인"
            }.get(new_claim.status, new_claim.status),
            "created_at": new_claim.created_at.isoformat(),
            "calculation_summary": {
                "total_clauses_checked": len(subscriptions),
                "applicable_clauses": len([r for r in calculation_results if r["calculated_amount"] > 0]),
                "total_calculated_amount": total_approved_amount
            },
            "calculation_details": calculation_results
        }
        
        # 불승인인 경우 사유 추가
        if new_claim.status == 'rejected':
            response["rejection_reason"] = "가입한 특약의 보장 조건에 해당하지 않습니다."
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"청구 생성 중 오류가 발생했습니다: {str(e)}")

@router.get("/user-claims", response_model=List[dict], summary="피보험자 청구 목록 조회", description="특정 피보험자의 모든 보험금 청구 목록을 조회합니다. 승인/불승인 상태, 보험금 계산 결과, 불승인 사유 포함.")
async def get_user_claims(
    patient_ssn: str,
    db: Session = Depends(get_db)
):
    """
    특정 피보험자의 모든 보험금 청구 목록을 조회합니다.
    
    - **patient_ssn**: 조회할 피보험자 주민등록번호
    - 피보험자의 모든 청구 내역을 최신순으로 조회
    - **승인/불승인 상태 정보 포함**: status_info.is_approved, status_info.is_rejected 등
    - **불승인 사유**: rejection_reason 필드로 확인
    - **보험금 정보**: original_claim_amount(원래 치료비) vs approved_amount(승인된 보험금)
    - 진단서 및 영수증 정보 포함
    """
    try:
        # 주민번호로 청구 조회
        claims = db.query(Claim).filter(
            Claim.patient_ssn == patient_ssn,
            Claim.is_deleted == False
        ).order_by(Claim.created_at.desc()).all()
        
        result = []
        for claim in claims:
            # 진단서 정보 조회
            diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == claim.diagnosis_id).first()
            # 영수증 정보 조회
            receipt = db.query(MedicalReceipt).filter(MedicalReceipt.id == claim.receipt_id).first()
            
            # 승인/불승인 상태 정보
            status_info = {
                "is_approved": claim.status in ["approved", "paid"],
                "is_rejected": claim.status == "rejected",
                "is_paid": claim.status == "paid",
                "status_korean": {
                    "pending": "심사중",
                    "approved": "승인",
                    "rejected": "불승인", 
                    "paid": "지급완료"
                }.get(claim.status, claim.status)
            }
            
            # 불승인 사유 추출
            rejection_reason = None
            if claim.status == "rejected" and "[불승인 사유]" in claim.claim_reason:
                rejection_reason = claim.claim_reason.split("[불승인 사유]")[-1].strip()
            
            result.append({
                "claim_id": claim.id,
                "patient_name": claim.patient_name,
                "patient_ssn": claim.patient_ssn,
                "original_claim_amount": receipt.total_amount if receipt else None,
                "approved_amount": claim.claim_amount if claim.status in ["approved", "paid"] else 0,
                "status": claim.status,
                "status_info": status_info,
                "rejection_reason": rejection_reason,
                "created_at": claim.created_at.isoformat(),
                "diagnosis_name": diagnosis.diagnosis_name if diagnosis else None,
                "hospital_name": diagnosis.hospital_name if diagnosis else None,
                "receipt_amount": receipt.total_amount if receipt else None,
                "receipt_date": receipt.receipt_date.isoformat() if receipt else None
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피보험자 청구 목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/all-claims", response_model=List[dict], summary="전체 청구 목록 조회", description="시스템의 모든 보험금 청구 목록을 조회합니다. 승인/불승인 상태, 계산 요약 정보 포함. (관리자용)")
async def get_all_claims(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    시스템의 모든 보험금 청구 목록을 조회합니다. (관리자용)
    
    - **skip**: 건너뛸 항목 수 (기본값: 0)
    - **limit**: 조회할 최대 항목 수 (기본값: 100)
    - 모든 사용자의 청구 내역을 최신순으로 조회
    - **승인/불승인 상태**: status_info 객체로 상세 정보 제공
    - **불승인 사유**: rejection_reason 필드로 확인  
    - **계산 요약**: calculation_summary로 특약 심사 결과 요약
    - **보험금 비교**: original_claim_amount vs approved_amount
    - 사용자 및 진단서 정보 포함
    """
    try:
        claims = db.query(Claim).filter(
            Claim.is_deleted == False
        ).order_by(Claim.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for claim in claims:
            # 사용자 정보 조회 (보험사 직원)
            user = db.query(User).filter(User.id == claim.user_id).first()
            # 진단서 정보 조회
            diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == claim.diagnosis_id).first()
            # 영수증 정보 조회
            receipt = db.query(MedicalReceipt).filter(MedicalReceipt.id == claim.receipt_id).first()
            
            # 승인/불승인 관련 추가 정보
            status_info = {
                "is_approved": claim.status in ["approved", "paid"],
                "is_rejected": claim.status == "rejected",
                "is_paid": claim.status == "paid",
                "status_korean": {
                    "pending": "심사중",
                    "approved": "승인",
                    "rejected": "불승인", 
                    "paid": "지급완료"
                }.get(claim.status, claim.status)
            }
            
            # 불승인 사유 추출 (claim_reason에서)
            rejection_reason = None
            if claim.status == "rejected" and "[불승인 사유]" in claim.claim_reason:
                rejection_reason = claim.claim_reason.split("[불승인 사유]")[-1].strip()
            
            # 계산 내역 조회 (간단 버전)
            calculations = db.query(ClaimCalculation).filter(
                ClaimCalculation.claim_id == claim.id,
                ClaimCalculation.is_deleted == False
            ).all()
            
            approved_calculations = [calc for calc in calculations if calc.calculated_amount > 0]
            total_calculated_amount = sum(calc.calculated_amount for calc in approved_calculations)
            
            result.append({
                "claim_id": claim.id,
                "user_id": claim.user_id,
                "user_name": user.name if user else None,
                "patient_name": claim.patient_name,
                "patient_ssn": claim.patient_ssn,
                "original_claim_amount": receipt.total_amount if receipt else None,
                "approved_amount": claim.claim_amount if claim.status in ["approved", "paid"] else 0,
                "status": claim.status,
                "status_info": status_info,
                "rejection_reason": rejection_reason,
                "created_at": claim.created_at.isoformat(),
                "diagnosis_name": diagnosis.diagnosis_name if diagnosis else None,
                "hospital_name": diagnosis.hospital_name if diagnosis else None,
                "receipt_amount": receipt.total_amount if receipt else None,
                "receipt_date": receipt.receipt_date.isoformat() if receipt else None,
                "calculation_summary": {
                    "total_clauses_checked": len(calculations),
                    "approved_clauses": len(approved_calculations),
                    "total_calculated_amount": total_calculated_amount
                }
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전체 청구 목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/claim/{claim_id}", response_model=dict, summary="특정 청구 상세 조회", description="특정 보험금 청구의 모든 상세 정보를 조회합니다. 가입 특약, 계산 내역, 승인/불승인 사유 등 포함.")
async def get_claim_detail(
    claim_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 보험금 청구의 상세 정보를 조회합니다.
    
    - **claim_id**: 조회할 청구 ID
    - **승인/불승인 상태**: status_info 객체로 상세 정보
    - **불승인 사유**: rejection_reason 필드
    - **가입 특약 목록**: subscribed_clauses 배열로 환자가 가입한 모든 특약 확인
    - **계산 내역**: calculation_details 배열로 각 특약별 심사 결과와 계산 로직 확인
    - **계산 요약**: calculation_summary로 전체 심사 결과 요약
    - **보험금 정보**: original_claim_amount vs approved_amount 비교
    - 진단서, 영수증 상세 정보 포함
    - 사용자 정보 포함
    
    이 API 하나로 청구의 모든 정보를 확인할 수 있습니다.
    """
    try:
        claim = db.query(Claim).filter(
            Claim.id == claim_id,
            Claim.is_deleted == False
        ).first()
        
        if not claim:
            raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다")
        
        # 사용자 정보 조회
        user = db.query(User).filter(User.id == claim.user_id).first()
        # 진단서 정보 조회
        diagnosis = db.query(MedicalDiagnosis).filter(MedicalDiagnosis.id == claim.diagnosis_id).first()
        # 영수증 정보 조회
        receipt = db.query(MedicalReceipt).filter(MedicalReceipt.id == claim.receipt_id).first()
        
        # 승인/불승인 상태 정보
        status_info = {
            "is_approved": claim.status in ["approved", "paid"],
            "is_rejected": claim.status == "rejected",
            "is_paid": claim.status == "paid",
            "status_korean": {
                "pending": "심사중",
                "approved": "승인",
                "rejected": "불승인", 
                "paid": "지급완료"
            }.get(claim.status, claim.status)
        }
        
        # 불승인 사유 추출
        rejection_reason = None
        if claim.status == "rejected" and "[불승인 사유]" in claim.claim_reason:
            rejection_reason = claim.claim_reason.split("[불승인 사유]")[-1].strip()
        
        # 계산 내역 상세 조회
        calculations = db.query(ClaimCalculation).filter(
            ClaimCalculation.claim_id == claim_id,
            ClaimCalculation.is_deleted == False
        ).all()
        
        calculation_details = []
        for calc in calculations:
            clause = db.query(InsuranceClause).filter(InsuranceClause.id == calc.clause_id).first()
            calculation_details.append({
                "clause_name": clause.clause_name if clause else "알 수 없음",
                "clause_category": clause.category if clause else None,
                "calculated_amount": calc.calculated_amount,
                "calculation_logic": calc.calculation_logic,
                "is_approved": calc.calculated_amount > 0
            })
        
        # 가입 특약 정보 조회
        subscriptions = db.query(UserSubscription).filter(
            UserSubscription.patient_ssn == claim.patient_ssn,
            UserSubscription.status == "active",
            UserSubscription.is_deleted == False
        ).all()
        
        subscription_details = []
        for sub in subscriptions:
            clause = db.query(InsuranceClause).filter(InsuranceClause.id == sub.clause_id).first()
            if clause:
                subscription_details.append({
                    "clause_name": clause.clause_name,
                    "clause_category": clause.category,
                    "per_unit": clause.per_unit,
                    "max_total": clause.max_total,
                    "unit_type": clause.unit_type,
                    "subscription_date": sub.subscription_date.isoformat()
                })
        
        result = {
            "claim_id": claim.id,
            "user_id": claim.user_id,
            "user_name": user.name if user else None,
            "original_claim_amount": receipt.total_amount if receipt else None,
            "approved_amount": claim.claim_amount if claim.status in ["approved", "paid"] else 0,
            "status": claim.status,
            "status_info": status_info,
            "rejection_reason": rejection_reason,
            "created_at": claim.created_at.isoformat(),
            "diagnosis": {
                "id": diagnosis.id if diagnosis else None,
                "patient_name": diagnosis.patient_name if diagnosis else None,
                "diagnosis_name": diagnosis.diagnosis_name if diagnosis else None,
                "diagnosis_date": diagnosis.diagnosis_date.isoformat() if diagnosis else None,
                "hospital_name": diagnosis.hospital_name if diagnosis else None,
                "doctor_name": diagnosis.doctor_name if diagnosis else None,
                "icd_code": diagnosis.icd_code if diagnosis else None,
                "admission_days": diagnosis.admission_days if diagnosis else None
            },
            "receipt": {
                "id": receipt.id if receipt else None,
                "patient_name": receipt.patient_name if receipt else None,
                "total_amount": receipt.total_amount if receipt else None,
                "receipt_date": receipt.receipt_date.isoformat() if receipt else None,
                "hospital_name": receipt.hospital_name if receipt else None,
                "treatment_details": receipt.treatment_details if receipt else None
            },
            "subscribed_clauses": subscription_details,
            "calculation_details": calculation_details,
            "calculation_summary": {
                "total_clauses_checked": len(calculations),
                "approved_clauses": len([c for c in calculations if c.calculated_amount > 0]),
                "total_calculated_amount": sum(c.calculated_amount for c in calculations)
            }
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"청구 상세 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/claims-summary", response_model=dict, summary="청구 통계 요약", description="보험금 청구 현황에 대한 통계 요약 정보를 제공합니다.")
async def get_claims_summary(db: Session = Depends(get_db)):
    """
    보험금 청구 현황에 대한 통계 요약 정보를 제공합니다.
    
    - 전체 청구 건수
    - 상태별 청구 건수 (pending, approved, rejected, paid)
    - 총 청구 금액
    - 평균 청구 금액
    - 최근 30일 청구 현황
    """
    try:
        from datetime import datetime, timedelta
        
        # 전체 청구 건수
        total_claims = db.query(Claim).filter(Claim.is_deleted == False).count()
        
        # 상태별 청구 건수
        pending_claims = db.query(Claim).filter(
            Claim.status == 'pending',
            Claim.is_deleted == False
        ).count()
        
        approved_claims = db.query(Claim).filter(
            Claim.status == 'approved',
            Claim.is_deleted == False
        ).count()
        
        rejected_claims = db.query(Claim).filter(
            Claim.status == 'rejected',
            Claim.is_deleted == False
        ).count()
        
        paid_claims = db.query(Claim).filter(
            Claim.status == 'paid',
            Claim.is_deleted == False
        ).count()
        
        # 총 청구 금액
        total_amount_result = db.query(Claim).filter(Claim.is_deleted == False).all()
        total_amount = sum(claim.claim_amount for claim in total_amount_result if claim.claim_amount)
        
        # 평균 청구 금액
        avg_amount = total_amount / total_claims if total_claims > 0 else 0
        
        # 최근 30일 청구 현황
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_claims = db.query(Claim).filter(
            Claim.created_at >= thirty_days_ago,
            Claim.is_deleted == False
        ).count()
        
        # 최고 청구 금액
        max_amount_claim = db.query(Claim).filter(
            Claim.is_deleted == False
        ).order_by(Claim.claim_amount.desc()).first()
        max_amount = max_amount_claim.claim_amount if max_amount_claim else 0
        
        # 승인율 계산
        approval_rate = (approved_claims + paid_claims) / total_claims * 100 if total_claims > 0 else 0
        
        result = {
            "total_claims": total_claims,
            "status_summary": {
                "pending": pending_claims,
                "approved": approved_claims,
                "rejected": rejected_claims,
                "paid": paid_claims,
                "approval_rate": round(approval_rate, 1)
            },
            "financial_summary": {
                "total_amount": total_amount,
                "average_amount": round(avg_amount, 2),
                "max_amount": max_amount
            },
            "recent_activity": {
                "claims_last_30_days": recent_claims
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"청구 통계 조회 중 오류가 발생했습니다: {str(e)}")

# 심사 처리 및 지급 처리는 별도의 관리자 시스템에서 처리
# 현재 API는 조회 위주로 구성

# 계산 내역은 특정 청구 상세 조회(GET /claim/{claim_id})에 포함됨

@router.delete("/claim/{claim_id}", response_model=dict, summary="보험금 청구 삭제", description="특정 보험금 청구를 삭제합니다. 실제로는 소프트 삭제(is_deleted=True)로 처리됩니다.")
async def delete_claim(
    claim_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 보험금 청구를 삭제합니다.
    
    - **claim_id**: 삭제할 청구 ID
    - 실제로는 데이터를 완전히 삭제하지 않고 is_deleted 플래그를 True로 설정 (소프트 삭제)
    - 관련된 계산 내역도 함께 소프트 삭제 처리
    - 삭제된 청구는 일반 조회 API에서 제외됨
    """
    try:
        # 청구 존재 확인
        claim = db.query(Claim).filter(
            Claim.id == claim_id,
            Claim.is_deleted == False
        ).first()
        
        if not claim:
            raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다")
        
        # 청구 소프트 삭제
        claim.is_deleted = True
        
        # 관련된 계산 내역도 소프트 삭제
        calculations = db.query(ClaimCalculation).filter(
            ClaimCalculation.claim_id == claim_id,
            ClaimCalculation.is_deleted == False
        ).all()
        
        for calculation in calculations:
            calculation.is_deleted = True
        
        db.commit()
        
        return {
            "message": "보험금 청구가 성공적으로 삭제되었습니다",
            "deleted_claim_id": claim_id,
            "patient_name": claim.patient_name,
            "patient_ssn": claim.patient_ssn,
            "original_amount": claim.claim_amount,
            "status_before_deletion": claim.status,
            "deleted_calculations_count": len(calculations),
            "deleted_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"청구 삭제 중 오류가 발생했습니다: {str(e)}") 