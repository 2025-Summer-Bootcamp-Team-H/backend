#!/usr/bin/env python3
"""
Enhanced Dummy Data Creation Script
- 20 realistic cases (14 passed, 6 failed)
- Diagnosis-clause matching logic
- 6 insurance employees, 20 patients
- Detailed claim information storage
"""

import sys
import os
import json
import random
from datetime import datetime, date, timedelta

# Add the backend directory to the Python path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(backend_dir)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.database import Base, get_db
from models.models import (
    User, InsuranceCompany, InsuranceProduct, InsuranceClause,
    MedicalDiagnosis, MedicalReceipt, Claim, UserContract, UserSubscription
)
from utils.auth import get_password_hash

# Database URL
DATABASE_URL = "postgresql://postgres:postgres123@postgres:5432/insurance_system"

def init_database():
    """Initialize database with fresh schema"""
    print("🔄 Initializing database...")
    
    engine = create_engine(DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialized successfully!")
    return engine

def load_extracted_clauses():
    """Load extracted insurance clauses from JSON files"""
    clauses = []
    
    output_dir = os.path.join(backend_dir, "output_results")
    files = [
        "삼성생명_스마트보장보험_extracted_clauses.json",
        "삼성생명_실손의료비보장보험_extracted_clauses.json", 
        "삼성생명_희망사랑보험_extracted_clauses.json"
    ]
    
    for filename in files:
        file_path = os.path.join(output_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_clauses = json.load(f)
                clauses.extend(file_clauses)
                print(f"📄 Loaded {len(file_clauses)} clauses from {filename}")
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
    
    return clauses

def create_users(db):
    """Create 5 insurance company employees (최일우 제외)"""
    print("\n👥 Creating 5 insurance employees...")
    
    users_data = [
        {"email": "admin@samsung.com", "name": "김태수", "password": "admin123"},
        {"email": "agent1@samsung.com", "name": "오유민", "password": "agent123"},
        {"email": "agent2@samsung.com", "name": "임윤환", "password": "agent123"},
        {"email": "manager@samsung.com", "name": "김다현", "password": "manager123"},
        {"email": "agent3@samsung.com", "name": "김수현", "password": "agent123"},
    ]
    
    for user_data in users_data:
        hashed_password = get_password_hash(user_data["password"])
        user = User(
            email=user_data["email"],
            name=user_data["name"],
            password=hashed_password
        )
        db.add(user)
        print(f"  👤 Created user: {user_data['name']} ({user_data['email']})")
    
    db.commit()
    print("✅ 5 insurance employees created successfully!")

def create_insurance_data(db):
    """Create insurance companies, products, and clauses from extracted data"""
    print("\n🏢 Creating insurance data...")
    
    extracted_clauses = load_extracted_clauses()
    print(f"📋 Total extracted clauses: {len(extracted_clauses)}")
    
    # Create Samsung Life Insurance Company
    company = InsuranceCompany(
        name="삼성생명",
        code="SAMSUNG_LIFE",
        is_active=True
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    print(f"  🏢 Created company: {company.name}")
    
    # Create insurance products
    products_data = [
        {
            "name": "스마트보장보험",
            "product_code": "SMART_PROTECTION",
            "description": "종합적인 보장을 제공하는 스마트 보험"
        },
        {
            "name": "실손의료비보장보험",
            "product_code": "MEDICAL_EXPENSE",
            "description": "의료비 실손을 보장하는 보험"
        },
        {
            "name": "희망사랑보험",
            "product_code": "HOPE_LOVE",
            "description": "사랑하는 가족을 위한 종합보험"
        }
    ]
    
    products = []
    for product_data in products_data:
        product = InsuranceProduct(
            company_id=company.id,
            name=product_data["name"],
            product_code=product_data["product_code"],
            description=product_data["description"],
            is_active=True
        )
        db.add(product)
        products.append(product)
        print(f"  📋 Created product: {product_data['name']}")
    
    db.commit()
    
    # Create insurance clauses from extracted data
    product_map = {
        "스마트보장보험": products[0].id,
        "실손의료비보장보험": products[1].id,
        "희망사랑보험": products[2].id
    }
    
    clause_objects = []
    for clause_data in extracted_clauses:
        # Determine product based on clause characteristics
        if "실손" in clause_data.get("category", "") or "입원의료비" in clause_data.get("category", ""):
            product_id = product_map["실손의료비보장보험"]
        elif "암" in clause_data.get("clause_name", ""):
            product_id = product_map["희망사랑보험"]
        else:
            product_id = product_map["스마트보장보험"]
        
        clause = InsuranceClause(
            clause_code=clause_data["id"],
            clause_name=clause_data["clause_name"],
            product_id=product_id,
            category=clause_data["category"],
            unit_type=clause_data["unit_type"],
            per_unit=clause_data["per_unit"],
            max_total=clause_data["max_total"],
            conditions=clause_data["condition"],
            description=f"{clause_data['clause_name']} - {clause_data['condition']}"
        )
        clause_objects.append(clause)
        db.add(clause)
    
    db.commit()
    print(f"📋 Created {len(clause_objects)} insurance clauses from extracted data")
    
    return clause_objects, products

def match_diagnosis_to_clauses(diagnosis_name, treatment_type, admission_days, medical_cost):
    """Match diagnosis to relevant insurance clauses"""
    diagnosis_lower = diagnosis_name.lower()
    
    # Define diagnosis-clause matching rules
    matching_rules = {
        # 암 관련
        "암": ["암진단특약", "암직접치료입원특약", "암직접치료수술특약"],
        "유방암": ["암진단특약", "암직접치료입원특약", "암직접치료수술특약"],
        "폐암": ["암진단특약", "암직접치료입원특약", "암직접치료수술특약"],
        "대장암": ["암진단특약", "암직접치료입원특약", "암직접치료수술특약"],
        "위암": ["암진단특약", "암직접치료입원특약", "암직접치료수술특약"],
        
        # 심장 관련
        "심근경색": ["중증질병진단특약", "중증질병입원특약", "중증질병수술특약"],
        "협심증": ["질병진단특약", "질병입원특약", "질병수술특약"],
        "부정맥": ["질병진단특약", "질병입원특약"],
        
        # 뇌 관련
        "뇌졸중": ["중증질병진단특약", "중증질병입원특약", "중증질병수술특약"],
        "뇌출혈": ["중증질병진단특약", "중증질병입원특약", "중증질병수술특약"],
        
        # 폐 관련
        "폐렴": ["질병진단특약", "질병입원특약", "질병치료특약"],
        "기관지염": ["질병진단특약", "질병통원특약"],
        
        # 소화기 관련
        "위염": ["질병진단특약", "질병통원특약"],
        "십이지장궤양": ["질병진단특약", "질병입원특약", "질병수술특약"],
        
        # 내분비 관련
        "당뇨병": ["질병진단특약", "질병통원특약", "질병치료특약"],
        "갑상선기능항진증": ["질병진단특약", "질병통원특약"],
        
        # 신장 관련
        "신증": ["중증질병진단특약", "중증질병입원특약", "중증질병치료특약"],
        "신부전": ["중증질병진단특약", "중증질병입원특약", "중증질병치료특약"],
        
        # 외상 관련
        "골절": ["상해입원특약", "상해수술특약"],
        "탈구": ["상해입원특약", "상해치료특약"],
        "절상": ["상해입원특약", "상해치료특약"],
        
        # 기타
        "고혈압": ["질병진단특약", "질병통원특약"],
        "관절염": ["질병진단특약", "질병통원특약", "질병치료특약"],
    }
    
    # Find matching clauses based on diagnosis
    matched_clauses = []
    for keyword, clauses in matching_rules.items():
        if keyword in diagnosis_lower:
            matched_clauses.extend(clauses)
            break
    
    # If no specific match, use general clauses based on treatment type
    if not matched_clauses:
        if treatment_type == "입원치료":
            matched_clauses = ["질병입원특약"]
        elif treatment_type == "수술":
            matched_clauses = ["질병수술특약"]
        elif treatment_type == "통원치료":
            matched_clauses = ["질병통원특약"]
        else:
            matched_clauses = ["질병진단특약"]
    
    return matched_clauses

def calculate_claim_amount(clause_names, clause_objects, diagnosis_name, treatment_type, admission_days, medical_cost):
    """Calculate claim amount based on matched clauses"""
    total_amount = 0
    applied_clauses = []
    
    for clause_name in clause_names:
        clause = next((c for c in clause_objects if c.clause_name == clause_name), None)
        if clause:
            amount = 0
            
            if clause.unit_type == "amount":
                if "입원" in clause.clause_name and admission_days > 0:
                    # Per day payment for hospitalization
                    amount = clause.per_unit * admission_days
                    amount = min(amount, clause.max_total)
                elif "진단" in clause.clause_name:
                    # One-time payment for diagnosis
                    amount = clause.per_unit
                elif "수술" in clause.clause_name and treatment_type == "수술":
                    # One-time payment for surgery
                    amount = clause.per_unit
                elif "통원" in clause.clause_name and treatment_type == "통원치료":
                    # Payment for outpatient treatment
                    amount = clause.per_unit
                else:
                    # General treatment coverage
                    amount = clause.per_unit
                
                total_amount += amount
                applied_clauses.append({
                    "clause_name": clause.clause_name,
                    "amount": amount,
                    "reason": f"{clause.clause_name} 적용"
                })
    
    return total_amount, applied_clauses

def create_realistic_patients():
    """Create 20 realistic patients with various medical conditions"""
    patients = [
        # Passed cases (14개) - 보험금 지급
        {
            "name": "박영수", "ssn": "850315-1234567", "diagnosis": "급성 심근경색증", 
            "hospital": "서울아산병원", "treatment_type": "입원치료", "medical_cost": 2500000, 
            "admission_days": 7, "expected_amount": 350000, "status": "passed"
        },
        {
            "name": "이미영", "ssn": "920728-2345678", "diagnosis": "유방암", 
            "hospital": "삼성서울병원", "treatment_type": "수술", "medical_cost": 5000000, 
            "admission_days": 14, "expected_amount": 1700000, "status": "passed"
        },
        {
            "name": "정민호", "ssn": "780612-1345678", "diagnosis": "당뇨병성 신증", 
            "hospital": "연세세브란스병원", "treatment_type": "통원치료", "medical_cost": 150000, 
            "admission_days": 0, "expected_amount": 150000, "status": "passed"
        },
        {
            "name": "최지원", "ssn": "950403-2456789", "diagnosis": "폐렴", 
            "hospital": "서울성모병원", "treatment_type": "입원치료", "medical_cost": 800000, 
            "admission_days": 5, "expected_amount": 500000, "status": "passed"
        },
        {
            "name": "강서연", "ssn": "881120-1567890", "diagnosis": "교통사고로 인한 다발성 골절", 
            "hospital": "한양대학교병원", "treatment_type": "수술", "medical_cost": 3200000, 
            "admission_days": 21, "expected_amount": 1050000, "status": "passed"
        },
        {
            "name": "윤준호", "ssn": "930515-1678901", "diagnosis": "뇌졸중", 
            "hospital": "고려대학교병원", "treatment_type": "입원치료", "medical_cost": 1800000, 
            "admission_days": 12, "expected_amount": 600000, "status": "passed"
        },
        {
            "name": "송은지", "ssn": "890722-1789012", "diagnosis": "위암", 
            "hospital": "서울대학교병원", "treatment_type": "수술", "medical_cost": 4500000, 
            "admission_days": 18, "expected_amount": 1900000, "status": "passed"
        },
        {
            "name": "한동현", "ssn": "910830-1890123", "diagnosis": "십이지장궤양", 
            "hospital": "경희대학교병원", "treatment_type": "입원치료", "medical_cost": 1200000, 
            "admission_days": 8, "expected_amount": 400000, "status": "passed"
        },
        {
            "name": "조성민", "ssn": "870415-1901234", "diagnosis": "고혈압", 
            "hospital": "분당차병원", "treatment_type": "통원치료", "medical_cost": 80000, 
            "admission_days": 0, "expected_amount": 80000, "status": "passed"
        },
        {
            "name": "임수진", "ssn": "940625-2012345", "diagnosis": "관절염", 
            "hospital": "부산대학교병원", "treatment_type": "통원치료", "medical_cost": 120000, 
            "admission_days": 0, "expected_amount": 120000, "status": "passed"
        },
        {
            "name": "배현우", "ssn": "860918-2123456", "diagnosis": "협심증", 
            "hospital": "전남대학교병원", "treatment_type": "입원치료", "medical_cost": 900000, 
            "admission_days": 6, "expected_amount": 300000, "status": "passed"
        },
        {
            "name": "신지은", "ssn": "920112-2234567", "diagnosis": "기관지염", 
            "hospital": "충남대학교병원", "treatment_type": "통원치료", "medical_cost": 60000, 
            "admission_days": 0, "expected_amount": 60000, "status": "passed"
        },
        {
            "name": "권태영", "ssn": "880725-2345678", "diagnosis": "갑상선기능항진증", 
            "hospital": "경북대학교병원", "treatment_type": "통원치료", "medical_cost": 100000, 
            "admission_days": 0, "expected_amount": 100000, "status": "passed"
        },
        {
            "name": "안서현", "ssn": "930328-2456789", "diagnosis": "부정맥", 
            "hospital": "전북대학교병원", "treatment_type": "입원치료", "medical_cost": 700000, 
            "admission_days": 4, "expected_amount": 200000, "status": "passed"
        },
        
        # Failed cases (6개) - 보험금 미지급
        {
            "name": "최일우", "ssn": "000830-3381025", "diagnosis": "감기", 
            "hospital": "동네의원", "treatment_type": "통원치료", "medical_cost": 15000, 
            "admission_days": 0, "expected_amount": 0, "status": "failed", "reason": "가입하지 않은 특약"
        },
        {
            "name": "김보험", "ssn": "850101-2567890", "diagnosis": "치아교정", 
            "hospital": "치과의원", "treatment_type": "통원치료", "medical_cost": 500000, 
            "admission_days": 0, "expected_amount": 0, "status": "failed", "reason": "치과치료는 보장하지 않음"
        },
        {
            "name": "이청구", "ssn": "920515-2678901", "diagnosis": "미용성형", 
            "hospital": "성형외과", "treatment_type": "수술", "medical_cost": 3000000, 
            "admission_days": 1, "expected_amount": 0, "status": "failed", "reason": "미용성형은 보장하지 않음"
        },
        {
            "name": "박매니저", "ssn": "780830-2789012", "diagnosis": "산전검사", 
            "hospital": "산부인과", "treatment_type": "통원치료", "medical_cost": 200000, 
            "admission_days": 0, "expected_amount": 0, "status": "failed", "reason": "산전검사는 보장하지 않음"
        },
        {
            "name": "김다현", "ssn": "950625-2890123", "diagnosis": "예방접종", 
            "hospital": "예방의학과", "treatment_type": "통원치료", "medical_cost": 80000, 
            "admission_days": 0, "expected_amount": 0, "status": "failed", "reason": "예방접종은 보장하지 않음"
        },
        {
            "name": "김수현", "ssn": "881215-2901234", "diagnosis": "피부미용", 
            "hospital": "피부과", "treatment_type": "통원치료", "medical_cost": 150000, 
            "admission_days": 0, "expected_amount": 0, "status": "failed", "reason": "미용치료는 보장하지 않음"
        }
    ]
    
    return patients

def match_and_calculate_realistic_clauses(patient_data, clause_objects):
    """
    진단서/영수증 항목에 따라 특약을 현실적으로 매칭하고 지급액 및 산정근거를 생성
    """
    diagnosis = patient_data["diagnosis"]
    treatment_type = patient_data["treatment_type"]
    admission_days = patient_data["admission_days"]
    medical_cost = patient_data["medical_cost"]
    receipt_items = patient_data.get("receipt_items", {})  # dict: 항목명→금액

    # 예시: 최일우 POC용 환자
    if patient_data["name"] == "최일우":
        # 보험가입: 실손의료비보장보험
        # 특약: 영상진단특약, MRI특약, 입원특약, 검사특약 등
        matched = []
        applied = []
        total_claim = 0.0
        # 1. 영상진단특약 (MRI)
        mri_sum = sum([v for k, v in receipt_items.items() if "MRI" in k or "영상진단" in k])
        mri_clause = next((c for c in clause_objects if "영상진단" in c.clause_name), None)
        if mri_clause and mri_sum > 0:
            amount = round(min(mri_sum * 0.8, mri_clause.max_total), 2)
            total_claim += amount
            matched.append(mri_clause.clause_name)
            applied.append({
                "clause_name": mri_clause.clause_name,
                "amount": amount,
                "description": mri_clause.description,
                "calculation_basis": f"MRI/영상진단료({mri_sum:,.2f}원) × 80% = {amount:,.2f}원"
            })
        # 2. 입원특약
        in_sum = sum([v for k, v in receipt_items.items() if "입원료" in k])
        in_clause = next((c for c in clause_objects if "입원특약" in c.clause_name), None)
        if in_clause and in_sum > 0:
            amount = round(min(in_sum, in_clause.max_total), 2)
            total_claim += amount
            matched.append(in_clause.clause_name)
            applied.append({
                "clause_name": in_clause.clause_name,
                "amount": amount,
                "description": in_clause.description,
                "calculation_basis": f"입원료({in_sum:,.2f}원) × 100% = {amount:,.2f}원"
            })
        # 3. 검사특약
        test_sum = sum([v for k, v in receipt_items.items() if "검사" in k])
        test_clause = next((c for c in clause_objects if "검사특약" in c.clause_name), None)
        if test_clause and test_sum > 0:
            amount = round(min(test_sum, test_clause.max_total), 2)
            total_claim += amount
            matched.append(test_clause.clause_name)
            applied.append({
                "clause_name": test_clause.clause_name,
                "amount": amount,
                "description": test_clause.description,
                "calculation_basis": f"검사료({test_sum:,.2f}원) × 100% = {amount:,.2f}원"
            })
        return total_claim, matched, applied
    # --- 이하 일반 환자 케이스 ---
    # 기존 로직을 현실적으로 보정(예: 지급액은 medical_cost 이하, 특약 한도 내, 소수점 허용)
    matched_clauses = match_diagnosis_to_clauses(diagnosis, treatment_type, admission_days, medical_cost)
    applied_clauses = []
    total_amount = 0.0
    for clause_name in matched_clauses:
        clause = next((c for c in clause_objects if c.clause_name == clause_name), None)
        if clause:
            # 현실적으로 지급액 산정
            if clause.unit_type == "amount":
                if "입원" in clause.clause_name and admission_days > 0:
                    amount = round(min(clause.per_unit * admission_days, clause.max_total, medical_cost), 2)
                    basis = f"입원특약: {admission_days}일 × {clause.per_unit:,.2f}원 = {amount:,.2f}원"
                elif "진단" in clause.clause_name:
                    amount = round(min(clause.per_unit, clause.max_total, medical_cost), 2)
                    basis = f"진단특약: {clause.per_unit:,.2f}원 지급 (최대 {clause.max_total:,.2f}원, 실제 {medical_cost:,.2f}원)"
                elif "수술" in clause.clause_name and treatment_type == "수술":
                    amount = round(min(clause.per_unit, clause.max_total, medical_cost), 2)
                    basis = f"수술특약: {clause.per_unit:,.2f}원 지급 (최대 {clause.max_total:,.2f}원, 실제 {medical_cost:,.2f}원)"
                elif "통원" in clause.clause_name and treatment_type == "통원치료":
                    amount = round(min(clause.per_unit, clause.max_total, medical_cost), 2)
                    basis = f"통원특약: {clause.per_unit:,.2f}원 지급 (최대 {clause.max_total:,.2f}원, 실제 {medical_cost:,.2f}원)"
                else:
                    amount = round(min(clause.per_unit, clause.max_total, medical_cost), 2)
                    basis = f"기타특약: {clause.per_unit:,.2f}원 지급 (최대 {clause.max_total:,.2f}원, 실제 {medical_cost:,.2f}원)"
                total_amount += amount
                applied_clauses.append({
                    "clause_name": clause.clause_name,
                    "amount": amount,
                    "description": clause.description,
                    "calculation_basis": basis
                })
    return total_amount, matched_clauses, applied_clauses

def create_medical_and_claim_data(db, clause_objects, products):
    """Create comprehensive medical and claim data for 20 patients"""
    print("\n🏥 Creating medical and claim data for 20 patients...")
    
    patients = create_realistic_patients()
    user_ids = [1, 2, 3, 4, 5]  # 5명의 보험사 직원
    
    passed_count = 0
    failed_count = 0
    
    for i, patient_data in enumerate(patients, 1):
        print(f"\n👤 Creating patient {i}/20: {patient_data['name']} ({patient_data['status']})")
        
        # Create medical diagnosis
        diagnosis_date = date.today() - timedelta(days=random.randint(1, 30))
        doctor_name = f"Dr. {random.choice(['김의사', '이의사', '박의사', '최의사', '정의사'])}"
        icd_code = f"K{random.randint(10, 99)}.{random.randint(0, 9)}"
        
        diagnosis = MedicalDiagnosis(
            user_id=user_ids[i % 5],  # 5명의 보험사 직원이 순차적으로 담당
            patient_name=patient_data["name"],
            patient_ssn=patient_data["ssn"],
            diagnosis_name=patient_data["diagnosis"],
            diagnosis_date=diagnosis_date,
            diagnosis_text=f"{patient_data['diagnosis']} - {patient_data['treatment_type']} 진행",
            hospital_name=patient_data["hospital"],
            doctor_name=doctor_name,
            icd_code=icd_code,
            admission_days=patient_data["admission_days"]
        )
        db.add(diagnosis)
        db.commit()
        db.refresh(diagnosis)
        
        # Create medical receipt
        receipt_date = diagnosis.diagnosis_date + timedelta(days=1)
        treatment_details = f"{patient_data['treatment_type']} - {patient_data['diagnosis']}"
        
        receipt = MedicalReceipt(
            user_id=user_ids[i % 5],
            patient_name=patient_data["name"],
            receipt_date=receipt_date,
            hospital_name=patient_data["hospital"],
            total_amount=patient_data["medical_cost"],
            treatment_details=treatment_details
        )
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        
        # Create UserContract for each patient (보험 가입 계약)
        # 환자별로 다른 보험상품 가입
        product_choice = i % 3  # 3개 보험상품 중 하나 선택
        selected_product = products[product_choice]
        
        # 계약번호 생성 (환자별 고유 번호)
        contract_number = f"CONTRACT-{patient_data['ssn'][:6]}-{i:03d}"
        
        # 계약 기간 설정 (1년 계약)
        start_date = date.today() - timedelta(days=random.randint(30, 365))
        end_date = start_date + timedelta(days=365)
        
        # 보험료 설정 (보험상품별로 다르게)
        premium_amounts = {
            "스마트보장보험": 50000,
            "실손의료비보장보험": 30000,
            "희망사랑보험": 80000
        }
        premium_amount = premium_amounts.get(selected_product.name, 50000)
        
        contract = UserContract(
            user_id=user_ids[i % 5],
            patient_name=patient_data["name"],
            patient_ssn=patient_data["ssn"],
            product_id=selected_product.id,
            contract_number=contract_number,
            start_date=start_date,
            end_date=end_date,
            premium_amount=premium_amount,
            status="active"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        print(f"  📋 Diagnosis: {patient_data['diagnosis']}")
        print(f"  🧾 Receipt: {patient_data['medical_cost']:,}원")
        print(f"  📄 Contract: {selected_product.name} 가입")
        
        # Create claim for all cases (passed and failed)
        if patient_data["status"] == "passed":
            # Match and calculate realistic clauses
            total_claim, matched_clauses, applied_clauses = match_and_calculate_realistic_clauses(patient_data, clause_objects)
            
            # Create detailed claim reason with subscription and matching info
            clause_details = []
            for clause_info in applied_clauses:
                clause_details.append(f"{clause_info['clause_name']}: {clause_info['amount']:,.2f}원")
            
            claim_reason = f"{patient_data['diagnosis']} 진단 및 치료 - " + ", ".join(clause_details)
            
            # Store detailed information including subscription and matching clauses
            detailed_info = {
                "patient_subscriptions": matched_clauses,  # 환자가 가입한 특약들
                "matched_clauses": matched_clauses,        # 매칭된 특약들
                "applied_clauses": applied_clauses,        # 실제 적용된 특약들
                "calculation_basis": f"진단명: {patient_data['diagnosis']}, 치료방법: {patient_data['treatment_type']}, 입원일수: {patient_data['admission_days']}일",
                "subscription_status": "가입됨",
                "matching_status": "매칭됨"
            }
            
            claim_reason += f" | 상세내역: {json.dumps(detailed_info, ensure_ascii=False)}"
            
            print(f"  💰 Claim: {total_claim:,.2f}원")
            print(f"  📝 Applied clauses: {', '.join(matched_clauses)}")
            passed_count += 1
            
        else:
            # Failed case - no matching, no calculation, just 0 amount
            total_claim = 0
            claim_reason = f"{patient_data['diagnosis']} - {patient_data.get('reason', '보장하지 않는 진료')}"
            
            # Store failed case detailed information
            detailed_info = {
                "patient_subscriptions": [],  # 가입한 특약 없음
                "matched_clauses": [],        # 매칭된 특약 없음
                "applied_clauses": [],        # 적용된 특약 없음
                "calculation_basis": f"진단명: {patient_data['diagnosis']}, 치료방법: {patient_data['treatment_type']}",
                "subscription_status": "미가입",
                "matching_status": "미매칭",
                "failure_reason": patient_data.get('reason', '보장하지 않는 진료')
            }
            
            claim_reason += f" | 상세내역: {json.dumps(detailed_info, ensure_ascii=False)}"
            
            print(f"  ❌ Failed reason: {patient_data.get('reason', '보장하지 않는 진료')} - 청구 생성 (0원)")
            failed_count += 1
        
        # Create claim for all cases
        # status 설정: claim_amount > 0이면 "passed", 0이면 "failed"
        claim_status = "passed" if total_claim > 0 else "failed"
        
        claim = Claim(
            user_id=user_ids[i % 5],
            patient_name=patient_data["name"],
            patient_ssn=patient_data["ssn"],
            diagnosis_id=diagnosis.id,
            receipt_id=receipt.id,
            claim_amount=total_claim,
            claim_reason=claim_reason,
            status=claim_status,
            created_at=datetime.utcnow()
        )
        db.add(claim)
        db.commit()
    
    print(f"\n✅ Medical and claim data created successfully!")
    print(f"   - 20 Patients with medical cases")
    print(f"   - {passed_count} Passed cases (보험금 지급)")
    print(f"   - {failed_count} Failed cases (보험금 미지급)")
    print(f"   - 20 Diagnoses")
    print(f"   - 20 Receipts")
    print(f"   - 20 UserContracts (보험 가입 계약)")
    print(f"   - 20 Claims (all cases)")

def main():
    """Main function to create all dummy data"""
    print("🚀 Starting Enhanced Dummy Data Creation...")
    
    # Initialize database
    engine = init_database()
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create all data
        create_users(db)
        clause_objects, products = create_insurance_data(db)
        create_medical_and_claim_data(db, clause_objects, products)
        
        print("\n🎉 All enhanced dummy data created successfully!")
        print("\n📊 Summary:")
        print("   - 5 Users (insurance employees)")
        print("   - 1 Insurance Company (삼성생명)")
        print("   - 3 Insurance Products")
        print(f"   - {len(clause_objects)} Insurance Clauses (from extracted data)")
        print("   - 20 Patients with medical cases")
        print("   - 14 Passed cases (보험금 지급)")
        print("   - 6 Failed cases (보험금 미지급)")
        print("   - Diagnosis-clause matching logic implemented")
        print("   - Detailed claim information stored")
        
    except Exception as e:
        print(f"❌ Error creating dummy data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main() 