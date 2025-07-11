from models.models import (
    InsuranceClause, MedicalReceipt, MedicalDiagnosis, 
    Claim, ClaimCalculation
)
from typing import List, Dict, Tuple
import re

class ClaimCalculator:
    def __init__(self, db_session):
        self.db = db_session
    
    def calculate_claim_amount(self, claim_id: int) -> Dict:
        """
        보험금 청구 금액을 계산합니다.
        """
        claim = self.db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError("청구 정보를 찾을 수 없습니다.")
        
        diagnosis = claim.diagnosis
        receipt = claim.receipt
        
        # 기존 계산 결과 삭제
        self.db.query(ClaimCalculation).filter(
            ClaimCalculation.claim_id == claim_id
        ).delete()
        
        calculations = []
        total_amount = 0
        
        # 1. 진단 관련 특약 계산
        diagnosis_amount, diagnosis_calcs = self._calculate_diagnosis_benefits(
            claim, diagnosis
        )
        calculations.extend(diagnosis_calcs)
        total_amount += diagnosis_amount
        
        # 2. 의료비 관련 특약 계산
        medical_amount, medical_calcs = self._calculate_medical_benefits(
            claim, receipt, diagnosis
        )
        calculations.extend(medical_calcs)
        total_amount += medical_amount
        
        # 3. 입원/통원 관련 특약 계산
        treatment_amount, treatment_calcs = self._calculate_treatment_benefits(
            claim, receipt, diagnosis
        )
        calculations.extend(treatment_calcs)
        total_amount += treatment_amount
        
        # 4. 총 보험금이 실제 의료비를 초과하지 않도록 제한
        actual_medical_cost = receipt.total_amount
        if total_amount > actual_medical_cost:
            print(f"⚠️ 총 보험금({total_amount:,.0f}원)이 실제 의료비({actual_medical_cost:,.0f}원)를 초과합니다.")
            
            # 비례 축소 적용
            reduction_ratio = actual_medical_cost / total_amount
            print(f"   축소 비율: {reduction_ratio:.2%}")
            
            for calc in calculations:
                original_amount = calc.calculated_amount
                calc.calculated_amount = original_amount * reduction_ratio
                calc.calculation_logic += f" → 의료비 한도 적용: {original_amount:,.0f} × {reduction_ratio:.2%} = {calc.calculated_amount:,.0f}원"
            
            total_amount = actual_medical_cost
        
        # 5. 계산 결과 저장
        for calc in calculations:
            self.db.add(calc)
        
        # 6. 청구 금액 업데이트
        claim.claim_amount = total_amount
        self.db.commit()
        
        return {
            "claim_id": claim_id,
            "total_amount": total_amount,
            "calculations": [
                {
                    "clause_name": calc.clause.clause_name,
                    "category": calc.clause.category,
                    "calculated_amount": calc.calculated_amount,
                    "calculation_logic": calc.calculation_logic
                }
                for calc in calculations
            ]
        }
    
    def _calculate_diagnosis_benefits(self, claim: Claim, diagnosis: MedicalDiagnosis) -> Tuple[float, List[ClaimCalculation]]:
        """진단 관련 특약 계산"""
        calculations = []
        total_amount = 0
        
        # 진단명에서 키워드 추출
        diagnosis_keywords = self._extract_diagnosis_keywords(diagnosis.diagnosis_name)
        
        # 관련 진단 특약 찾기
        diagnosis_clauses = self.db.query(InsuranceClause).filter(
            InsuranceClause.category == "진단"
        ).all()
        
        for clause in diagnosis_clauses:
            if self._is_clause_applicable(clause, diagnosis_keywords):
                # 진단 특약은 보통 정액 지급
                amount = clause.per_unit
                
                calculation = ClaimCalculation(
                    claim_id=claim.id,
                    clause_id=clause.id,
                    calculated_amount=amount,
                    calculation_logic=f"진단 특약 '{clause.clause_name}': {diagnosis.diagnosis_name} 진단으로 {amount:,.0f}원 지급"
                )
                calculations.append(calculation)
                total_amount += amount
        
        return total_amount, calculations
    
    def _calculate_medical_benefits(self, claim: Claim, receipt: MedicalReceipt, diagnosis: MedicalDiagnosis) -> Tuple[float, List[ClaimCalculation]]:
        """의료비 관련 특약 계산"""
        calculations = []
        total_amount = 0
        
        # 의료비 관련 특약 찾기
        medical_clauses = self.db.query(InsuranceClause).filter(
            InsuranceClause.category.in_(["의료비", "실손"])
        ).all()
        
        for clause in medical_clauses:
            # 실손 의료비는 실제 지출 금액의 일정 비율
            if "실손" in clause.clause_name:
                # 보통 80-90% 보장
                coverage_rate = 0.8
                deductible = 20000  # 공제금액 2만원
                
                # 공제금액을 제외한 실제 보장 금액
                covered_amount = max(0, receipt.total_amount - deductible)
                amount = min(covered_amount * coverage_rate, clause.per_unit)
                
                if amount > 0:
                    calculation = ClaimCalculation(
                        claim_id=claim.id,
                        clause_id=clause.id,
                        calculated_amount=amount,
                        calculation_logic=f"실손 의료비 '{clause.clause_name}': ({receipt.total_amount:,.0f} - {deductible:,.0f}) × {coverage_rate:.0%} = {amount:,.0f}원"
                    )
                    calculations.append(calculation)
                    total_amount += amount
        
        return total_amount, calculations
    
    def _calculate_treatment_benefits(self, claim: Claim, receipt: MedicalReceipt, diagnosis: MedicalDiagnosis) -> Tuple[float, List[ClaimCalculation]]:
        """치료/통원 관련 특약 계산"""
        calculations = []
        total_amount = 0
        
        # 입원/통원 구분
        is_inpatient = diagnosis.admission_days > 0
        treatment_type = "입원" if is_inpatient else "외래"
        
        # 관련 특약 찾기
        treatment_clauses = self.db.query(InsuranceClause).filter(
            InsuranceClause.category.in_(["외래진료", "입원", "통원"])
        ).all()
        
        for clause in treatment_clauses:
            applicable = False
            
            # 외래 진료 특약
            if "외래" in clause.clause_name and not is_inpatient:
                applicable = True
            # 입원 특약
            elif "입원" in clause.clause_name and is_inpatient:
                applicable = True
            # 통원 특약 (외래와 유사)
            elif "통원" in clause.clause_name and not is_inpatient:
                applicable = True
            
            if applicable:
                if is_inpatient:
                    # 입원일수 × 일당
                    amount = min(diagnosis.admission_days * clause.per_unit, clause.max_total)
                    logic = f"{treatment_type} 특약 '{clause.clause_name}': {diagnosis.admission_days}일 × {clause.per_unit:,.0f}원 = {amount:,.0f}원"
                else:
                    # 외래는 실제 의료비와 특약 한도 중 작은 값
                    amount = min(receipt.total_amount, clause.per_unit)
                    logic = f"{treatment_type} 특약 '{clause.clause_name}': min({receipt.total_amount:,.0f}, {clause.per_unit:,.0f}) = {amount:,.0f}원"
                
                calculation = ClaimCalculation(
                    claim_id=claim.id,
                    clause_id=clause.id,
                    calculated_amount=amount,
                    calculation_logic=logic
                )
                calculations.append(calculation)
                total_amount += amount
        
        return total_amount, calculations
    
    def _extract_diagnosis_keywords(self, diagnosis_name: str) -> List[str]:
        """진단명에서 키워드 추출"""
        keywords = []
        
        # 골절 관련
        if "골절" in diagnosis_name:
            keywords.append("골절")
        
        # 암 관련
        if any(word in diagnosis_name for word in ["암", "종양", "cancer"]):
            keywords.append("암")
        
        # 심장 관련
        if any(word in diagnosis_name for word in ["심장", "심근", "협심증"]):
            keywords.append("심장")
        
        # 뇌 관련
        if any(word in diagnosis_name for word in ["뇌", "중풍", "뇌졸중"]):
            keywords.append("뇌")
        
        return keywords
    
    def _is_clause_applicable(self, clause: InsuranceClause, keywords: List[str]) -> bool:
        """특약이 해당 진단에 적용 가능한지 확인"""
        clause_name = clause.clause_name.lower()
        
        for keyword in keywords:
            if keyword in clause_name:
                return True
        
        return False
    
    def calculate_claim_with_subscriptions(self, claim_id: int, subscriptions: List) -> Dict:
        """
        사용자의 특약 구독 정보를 기반으로 보험금을 계산합니다.
        """
        from models.models import UserSubscription  # 순환 import 방지
        
        claim = self.db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError("청구 정보를 찾을 수 없습니다.")
        
        diagnosis = claim.diagnosis
        receipt = claim.receipt
        
        # 기존 계산 결과 삭제
        self.db.query(ClaimCalculation).filter(
            ClaimCalculation.claim_id == claim_id
        ).delete()
        
        calculations = []
        total_amount = 0
        
        # 사용자가 구독한 특약들만 계산
        for subscription in subscriptions:
            clause = subscription.clause
            
            # 진단명에서 키워드 추출
            diagnosis_keywords = self._extract_diagnosis_keywords(diagnosis.diagnosis_name)
            
            # 특약 적용 가능 여부 확인
            if self._is_subscription_applicable(clause, diagnosis, receipt):
                amount = self._calculate_subscription_amount(clause, diagnosis, receipt)
                
                if amount > 0:
                    calculation = ClaimCalculation(
                        claim_id=claim_id,
                        clause_id=clause.id,
                        calculated_amount=amount,
                        calculation_logic=self._get_calculation_logic(clause, diagnosis, receipt, amount)
                    )
                    calculations.append(calculation)
                    total_amount += amount
        
        # 총 보험금이 실제 의료비를 초과하지 않도록 제한
        actual_medical_cost = receipt.total_amount
        if total_amount > actual_medical_cost:
            reduction_ratio = actual_medical_cost / total_amount
            
            for calc in calculations:
                original_amount = calc.calculated_amount
                calc.calculated_amount = original_amount * reduction_ratio
                calc.calculation_logic += f" → 의료비 한도 적용: {original_amount:,.0f} × {reduction_ratio:.2%} = {calc.calculated_amount:,.0f}원"
            
            total_amount = actual_medical_cost
        
        # 계산 결과 저장
        for calc in calculations:
            self.db.add(calc)
        
        # 청구 금액 업데이트
        claim.claim_amount = total_amount
        self.db.commit()
        
        return {
            "claim_id": claim_id,
            "total_amount": total_amount,
            "calculations": [
                {
                    "clause_name": calc.clause.clause_name,
                    "category": calc.clause.category,
                    "calculated_amount": calc.calculated_amount,
                    "calculation_logic": calc.calculation_logic
                }
                for calc in calculations
            ]
        }
    
    def _is_subscription_applicable(self, clause: InsuranceClause, diagnosis, receipt) -> bool:
        """특약이 해당 케이스에 적용 가능한지 확인"""
        clause_name = clause.clause_name.lower()
        diagnosis_name = diagnosis.diagnosis_name.lower()
        category = clause.category.lower()
        
        # 암 관련 특약
        if "암" in clause_name:
            return "암" in diagnosis_name or "cancer" in diagnosis_name.lower()
        
        # 골절 관련 특약
        if "골절" in clause_name:
            return "골절" in diagnosis_name
        
        # 입원 관련 특약
        if "입원" in clause_name or "입원" in category:
            return diagnosis.admission_days > 0
        
        # 외래/통원 관련 특약
        if any(word in clause_name for word in ["외래", "통원"]) or any(word in category for word in ["외래", "통원"]):
            return diagnosis.admission_days == 0
        
        # 진단 관련 특약
        if "진단" in clause_name or "진단" in category:
            return True  # 모든 진단에 적용 가능
        
        # 수술 관련 특약 (수술 키워드가 있는 경우)
        if "수술" in clause_name:
            return "수술" in diagnosis.diagnosis_text or "절제" in diagnosis.diagnosis_text
        
        # 질병 관련 특약
        if "질병" in clause_name:
            return True  # 모든 질병에 적용 가능
        
        # 상해 관련 특약
        if "상해" in clause_name:
            # ICD 코드 S로 시작하는 경우 상해
            return diagnosis.icd_code and diagnosis.icd_code.startswith("S")
        
        return False
    
    def _calculate_subscription_amount(self, clause: InsuranceClause, diagnosis, receipt) -> float:
        """특약별 보험금 계산"""
        category = clause.category.lower()
        clause_name = clause.clause_name.lower()
        
        # 진단 특약 - 정액 지급
        if "진단" in clause_name or "진단" in category:
            return clause.per_unit
        
        # 입원 특약 - 입원일수 × 일당
        if "입원" in clause_name or "입원" in category:
            if diagnosis.admission_days > 0:
                return min(diagnosis.admission_days * clause.per_unit, clause.max_total)
            return 0
        
        # 외래/통원 특약 - 실제 의료비와 특약 한도 중 작은 값
        if any(word in clause_name for word in ["외래", "통원"]) or any(word in category for word in ["외래", "통원"]):
            if diagnosis.admission_days == 0:
                return min(receipt.total_amount, clause.per_unit)
            return 0
        
        # 수술 특약 - 정액 지급
        if "수술" in clause_name:
            if "수술" in diagnosis.diagnosis_text or "절제" in diagnosis.diagnosis_text:
                return clause.per_unit
            return 0
        
        # 기타 특약 - 정액 지급
        return clause.per_unit
    
    def _get_calculation_logic(self, clause: InsuranceClause, diagnosis, receipt, amount: float) -> str:
        """계산 로직 설명 생성"""
        category = clause.category.lower()
        clause_name = clause.clause_name.lower()
        
        if "진단" in clause_name or "진단" in category:
            return f"진단 특약 '{clause.clause_name}': {diagnosis.diagnosis_name} 진단으로 {amount:,.0f}원 지급"
        
        if "입원" in clause_name or "입원" in category:
            return f"입원 특약 '{clause.clause_name}': {diagnosis.admission_days}일 × {clause.per_unit:,.0f}원 = {amount:,.0f}원"
        
        if any(word in clause_name for word in ["외래", "통원"]) or any(word in category for word in ["외래", "통원"]):
            return f"외래/통원 특약 '{clause.clause_name}': min({receipt.total_amount:,.0f}, {clause.per_unit:,.0f}) = {amount:,.0f}원"
        
        if "수술" in clause_name:
            return f"수술 특약 '{clause.clause_name}': {diagnosis.diagnosis_name} 수술로 {amount:,.0f}원 지급"
        
        return f"특약 '{clause.clause_name}': {amount:,.0f}원 지급" 