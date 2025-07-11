#!/usr/bin/env python3
"""
승인/불승인 더미 데이터 생성 스크립트

이 스크립트는 보험금 청구의 승인/불승인 케이스를 포함한 
현실적인 더미 데이터를 생성합니다.

승인/불승인 케이스:
1. 승인: 특약 가입 + 조건 충족 → 보험금 지급
2. 불승인: 특약 미가입 → 보험금 0원
3. 불승인: 조건 불충족 → 보험금 0원
4. 불승인: 보장 대상 아님 → 보험금 0원
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy.orm import Session
from models.database import engine
from models.models import *
from datetime import datetime, date, timedelta
import random

def create_approval_rejection_cases(db: Session):
    """승인/불승인 케이스를 포함한 더미 데이터 생성"""
    
    print("🔄 승인/불승인 케이스 더미 데이터 생성 시작...")
    
    # 기존 데이터 조회
    users = db.query(User).all()
    clauses = db.query(InsuranceClause).all()
    contracts = db.query(UserContract).all()
    
    if not users or not clauses or not contracts:
        print("❌ 기본 데이터가 없습니다. 먼저 create_final_dummy_data.py를 실행하세요.")
        return
    
    # 새로운 환자들 (승인/불승인 케이스용)
    new_patients = [
        {
            "name": "김승인",
            "ssn": "850315-1234567",
            "case_type": "approved",  # 특약 가입, 조건 충족 → 승인
            "diagnosis": "급성 맹장염",
            "hospital": "서울대학교병원",
            "cost": 1200000,
            "admission_days": 5
        },
        {
            "name": "이불승인",
            "ssn": "900822-2345678", 
            "case_type": "rejected_no_coverage",  # 특약 미가입 → 불승인
            "diagnosis": "치아 임플란트",
            "hospital": "강남치과병원",
            "cost": 800000,
            "admission_days": 0
        },
        {
            "name": "박불승인",
            "ssn": "780505-1345679",
            "case_type": "rejected_conditions",  # 조건 불충족 → 불승인
            "diagnosis": "경미한 위염",
            "hospital": "동네병원",
            "cost": 150000,
            "admission_days": 1  # 입원 특약 조건(3일 이상) 불충족
        },
        {
            "name": "최불승인",
            "ssn": "920101-2456789",
            "case_type": "rejected_not_covered",  # 보장 대상 아님 → 불승인
            "diagnosis": "미용 성형수술",
            "hospital": "강남성형외과",
            "cost": 3000000,
            "admission_days": 0  # 미용 목적은 보장 안됨
        },
        {
            "name": "한승인",
            "ssn": "750620-1567890",
            "case_type": "approved",  # 특약 가입, 조건 충족 → 승인
            "diagnosis": "교통사고 골절",
            "hospital": "아산병원",
            "cost": 2500000,
            "admission_days": 7
        }
    ]
    
    print("👥 새로운 환자 케이스 생성 중...")
    
    created_cases = []
    user_id = users[0].id  # 첫 번째 보험사 직원 사용
    
    for patient in new_patients:
        print(f"  📝 {patient['name']} ({patient['case_type']}) 케이스 생성...")
        
        # 1. 진단서 생성
        diagnosis = MedicalDiagnosis(
            user_id=user_id,
            patient_name=patient["name"],
            patient_ssn=patient["ssn"],
            diagnosis_name=patient["diagnosis"],
            diagnosis_date=date.today() - timedelta(days=random.randint(1, 30)),
            diagnosis_text=f"{patient['diagnosis']} 진단",
            hospital_name=patient["hospital"],
            doctor_name=f"김의사",
            admission_days=patient["admission_days"],
            image_url=f"/uploads/diagnosis/{patient['ssn']}.jpg"
        )
        db.add(diagnosis)
        db.flush()
        
        # 2. 영수증 생성
        receipt = MedicalReceipt(
            user_id=user_id,
            patient_name=patient["name"],
            receipt_date=diagnosis.diagnosis_date + timedelta(days=1),
            total_amount=patient["cost"],
            hospital_name=patient["hospital"],
            treatment_details=f"{patient['diagnosis']} 치료",
            image_url=f"/uploads/receipts/{patient['ssn']}.jpg"
        )
        db.add(receipt)
        db.flush()
        
        # 3. 케이스별 특약 가입 상태 설정
        subscribed_clauses = []
        
        if patient["case_type"] == "approved":
            # 승인 케이스: 해당하는 특약들 가입
            if "맹장염" in patient["diagnosis"]:
                # 입원, 수술 특약 가입
                relevant_clauses = [c for c in clauses if any(keyword in c.clause_name for keyword in ["입원", "수술"])]
                subscribed_clauses = relevant_clauses[:2]  
            elif "골절" in patient["diagnosis"]:
                # 상해, 입원 특약 가입
                relevant_clauses = [c for c in clauses if any(keyword in c.clause_name for keyword in ["상해", "입원"])]
                subscribed_clauses = relevant_clauses[:2]
                
        elif patient["case_type"] in ["rejected_no_coverage", "rejected_conditions", "rejected_not_covered"]:
            # 불승인 케이스들
            if patient["case_type"] == "rejected_no_coverage":
                # 특약 미가입
                subscribed_clauses = []
            elif patient["case_type"] == "rejected_conditions":
                # 입원 특약은 있지만 조건 불충족 (입원일수 부족)
                hospital_clauses = [c for c in clauses if "입원" in c.clause_name]
                subscribed_clauses = hospital_clauses[:1]
            elif patient["case_type"] == "rejected_not_covered":
                # 특약은 있지만 보장 대상 아님 (미용 목적)
                general_clauses = [c for c in clauses if any(keyword in c.clause_name for keyword in ["수술", "진단"])]
                subscribed_clauses = general_clauses[:1]
        
        # 4. 계약 생성 (특약이 있는 경우만)
        if subscribed_clauses:
            contract = UserContract(
                user_id=user_id,
                patient_name=patient["name"],
                patient_ssn=patient["ssn"],
                product_id=contracts[0].product_id,  # 기존 상품 사용
                contract_number=f"CONT-{patient['ssn'][-4:]}-{random.randint(1000, 9999)}",
                start_date=date.today() - timedelta(days=365),
                end_date=date.today() + timedelta(days=365),
                premium_amount=random.randint(50000, 200000),
                status="active"
            )
            db.add(contract)
            db.flush()
            
            # 5. 특약 가입 생성
            for clause in subscribed_clauses:
                subscription = UserSubscription(
                    user_id=user_id,
                    patient_name=patient["name"],
                    patient_ssn=patient["ssn"],
                    contract_id=contract.id,
                    clause_id=clause.id,
                    subscription_date=contract.start_date,
                    status="active"
                )
                db.add(subscription)
        
        # 6. 보험금 청구 생성
        claim = Claim(
            user_id=user_id,
            patient_name=patient["name"],
            patient_ssn=patient["ssn"],
            diagnosis_id=diagnosis.id,
            receipt_id=receipt.id,
            claim_amount=patient["cost"],
            claim_reason=f"{patient['diagnosis']} 치료비 청구",
            status="pending"  # 일단 대기 상태로 생성
        )
        db.add(claim)
        db.flush()
        
        # 7. 승인/불승인 처리 로직
        total_approved_amount = 0
        rejection_reason = None
        final_status = "rejected"  # 기본값은 불승인
        
        if patient["case_type"] == "approved":
            # 승인 케이스: 특약별 보험금 계산
            for clause in subscribed_clauses:
                approved_amount = 0
                
                # 입원 관련 특약
                if "입원" in clause.clause_name and patient["admission_days"] >= 3:
                    if clause.unit_type == "amount":
                        approved_amount = min(clause.per_unit * patient["admission_days"], clause.max_total)
                    else:  # percentage
                        approved_amount = min(patient["cost"] * (clause.per_unit / 100), clause.max_total)
                
                # 수술 관련 특약
                elif "수술" in clause.clause_name and ("수술" in patient["diagnosis"] or patient["admission_days"] > 0):
                    if clause.unit_type == "amount":
                        approved_amount = min(clause.per_unit, clause.max_total)
                    else:  # percentage
                        approved_amount = min(patient["cost"] * (clause.per_unit / 100), clause.max_total)
                
                # 상해 관련 특약
                elif "상해" in clause.clause_name and any(keyword in patient["diagnosis"] for keyword in ["골절", "사고", "외상"]):
                    if clause.unit_type == "amount":
                        approved_amount = min(clause.per_unit, clause.max_total)
                    else:  # percentage
                        approved_amount = min(patient["cost"] * (clause.per_unit / 100), clause.max_total)
                
                total_approved_amount += approved_amount
                
                # 계산 내역 저장
                if approved_amount > 0:
                    calculation = ClaimCalculation(
                        claim_id=claim.id,
                        clause_id=clause.id,
                        calculated_amount=approved_amount,
                        calculation_logic=f"{clause.clause_name}: {approved_amount:,.0f}원 지급"
                    )
                    db.add(calculation)
            
            # 보험금이 나오면 승인
            if total_approved_amount > 0:
                final_status = "approved"
                claim.claim_amount = total_approved_amount
            else:
                final_status = "rejected"
                rejection_reason = "가입된 특약의 보장 조건을 충족하지 않습니다."
                
        else:
            # 불승인 케이스들
            if patient["case_type"] == "rejected_no_coverage":
                rejection_reason = "해당 질병에 대한 보장 특약에 가입하지 않으셨습니다."
            elif patient["case_type"] == "rejected_conditions":
                rejection_reason = f"입원일수 {patient['admission_days']}일로 최소 입원 기준(3일 이상)을 충족하지 않습니다."
            elif patient["case_type"] == "rejected_not_covered":
                rejection_reason = "미용 목적의 수술은 보장 대상이 아닙니다."
        
        # 청구 상태 업데이트
        claim.status = final_status
        if rejection_reason:
            claim.claim_reason = f"{claim.claim_reason}\n[불승인 사유] {rejection_reason}"
        
        created_cases.append({
            "patient": patient,
            "claim_id": claim.id,
            "status": claim.status,
            "approved_amount": total_approved_amount,
            "rejection_reason": rejection_reason
        })
    
    db.commit()
    
    # 결과 출력
    print("\n✅ 승인/불승인 케이스 생성 완료!")
    print("\n📊 생성된 케이스 요약:")
    
    for case in created_cases:
        patient = case["patient"]
        print(f"\n👤 {patient['name']}")
        print(f"   🏥 진단: {patient['diagnosis']}")
        print(f"   💰 치료비: {patient['cost']:,}원")
        print(f"   📋 청구 ID: {case['claim_id']}")
        
        if case['status'] == 'approved':
            print(f"   ✅ 승인 - 보험금: {case['approved_amount']:,.0f}원")
        else:
            print(f"   ❌ 불승인 - 사유: {case['rejection_reason']}")
    
    return created_cases

def update_existing_claims_status(db: Session):
    """기존 청구 건들의 상태를 현실적으로 업데이트"""
    
    print("\n🔄 기존 청구 건 상태 업데이트 중...")
    
    existing_claims = db.query(Claim).filter(Claim.status == "pending").all()
    
    for i, claim in enumerate(existing_claims):
        # 환자별로 다른 결과 설정
        if "최일우" in claim.patient_name:
            # 최일우는 승인 (우리가 만든 메인 케이스)
            claim.status = "approved"
            print(f"  ✅ {claim.patient_name}: 승인")
            
        elif i % 3 == 0:
            # 33% 불승인
            claim.status = "rejected" 
            print(f"  ❌ {claim.patient_name}: 불승인")
            
        elif i % 3 == 1:
            # 33% 지급 완료
            claim.status = "paid"
            print(f"  💰 {claim.patient_name}: 지급 완료")
            
        else:
            # 34% 승인
            claim.status = "approved"
            print(f"  ✅ {claim.patient_name}: 승인")
    
    db.commit()
    print("  ✅ 기존 청구 건 상태 업데이트 완료")

def main():
    """메인 실행 함수"""
    print("🚀 승인/불승인 케이스 더미 데이터 생성 시작")
    print("=" * 50)
    
    # 데이터베이스 연결
    db = Session(engine)
    
    try:
        # 1. 새로운 승인/불승인 케이스 생성
        cases = create_approval_rejection_cases(db)
        
        # 2. 기존 청구 건들의 상태 업데이트
        update_existing_claims_status(db)
        
        print("\n" + "=" * 50)
        print("🎉 모든 작업 완료!")
        print("\n📈 최종 통계:")
        
        # 통계 조회
        total_claims = db.query(Claim).count()
        approved_claims = db.query(Claim).filter(Claim.status == "approved").count()
        rejected_claims = db.query(Claim).filter(Claim.status == "rejected").count()
        paid_claims = db.query(Claim).filter(Claim.status == "paid").count()
        pending_claims = db.query(Claim).filter(Claim.status == "pending").count()
        
        print(f"  📊 전체 청구: {total_claims}건")
        print(f"  ✅ 승인: {approved_claims}건 ({approved_claims/total_claims*100:.1f}%)")
        print(f"  ❌ 불승인: {rejected_claims}건 ({rejected_claims/total_claims*100:.1f}%)")
        print(f"  💰 지급완료: {paid_claims}건 ({paid_claims/total_claims*100:.1f}%)")
        print(f"  ⏳ 대기: {pending_claims}건 ({pending_claims/total_claims*100:.1f}%)")
        
        print(f"\n🔍 API 테스트:")
        print(f"  GET /v1/claims/all-claims - 모든 청구 상태 확인")
        print(f"  GET /v1/claims/claims-summary - 승인/불승인 통계")
        print(f"  POST /v1/claims/process-claim/{{claim_id}}?action=approve - 청구 승인")
        print(f"  POST /v1/claims/process-claim/{{claim_id}}?action=reject - 청구 불승인")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main() 