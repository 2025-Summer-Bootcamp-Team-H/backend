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
from faker import Faker
from pathlib import Path

# Add the backend directory to the Python path for imports
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

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

def debug_environment():
    """환경 정보 디버깅"""
    print("🔍 Environment Debug Info:")
    print(f"  Python version: {sys.version}")
    print(f"  Platform: {sys.platform}")
    print(f"  Current working directory: {os.getcwd()}")
    print(f"  Script location: {__file__}")
    print(f"  Backend directory: {backend_dir}")
    
    # 환경변수 확인
    env_vars = ['LANG', 'LC_ALL', 'LC_CTYPE', 'PYTHONIOENCODING', 'PYTHONUTF8']
    for var in env_vars:
        value = os.getenv(var, 'Not set')
        print(f"  {var}: {value}")
    
    # 파일 시스템 확인
    try:
        import locale
        print(f"  Default locale: {locale.getdefaultlocale()}")
        print(f"  Preferred locale: {locale.getpreferredencoding()}")
    except Exception as e:
        print(f"  Locale error: {e}")

def init_database():
    """Initialize database with fresh schema"""
    print("🔄 Initializing database...")
    
    engine = create_engine(DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialized successfully!")
    return engine

def load_extracted_clauses():
    debug_environment()
    clauses = []

    # 여러 후보 경로를 순서대로 시도
    candidate_dirs = [
        Path(__file__).parent / "output_results",  # 기존 방식
        Path(__file__).parent.parent / "output_results",  # backend/backend/output_results
        Path("/app/backend/output_results"),  # 컨테이너 절대경로
        Path("/app/output_results"),  # 컨테이너 절대경로(루트)
    ]
    output_dir = None
    for cand in candidate_dirs:
        if cand.exists():
            output_dir = cand
            break

    if output_dir is None:
        print("❌ output_results 폴더를 찾을 수 없습니다. 시도한 경로들:")
        for cand in candidate_dirs:
            print("  -", cand.resolve())
        return clauses

    print(f"✅ output_results 폴더 발견: {output_dir.resolve()}")

    try:
        dir_contents = list(output_dir.iterdir())
        print(f"📁 Directory contents: {[str(f) for f in dir_contents]}")
    except Exception as e:
        print(f"❌ Error reading directory: {e}")
        return clauses

    files = [
        "삼성생명_스마트보장보험_extracted_clauses.json",
        "삼성생명_실손의료비보장보험_extracted_clauses.json",
        "삼성생명_희망사랑보험_extracted_clauses.json"
    ]

    for filename in files:
        file_path = output_dir / filename
        print(f"🔍 Checking file: {file_path.resolve()}")
        try:
            if not file_path.exists():
                print(f"⚠️ File not found: {filename}")
                continue
            file_size = file_path.stat().st_size
            print(f"📊 File size: {file_size} bytes")
            if file_size == 0:
                print(f"⚠️ Empty file: {filename}")
                continue
            encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']
            file_clauses = None
            for encoding in encodings:
                try:
                    with file_path.open('r', encoding=encoding) as f:
                        file_clauses = json.load(f)
                        print(f"✅ Successfully loaded with {encoding} encoding")
                        break
                except UnicodeDecodeError:
                    print(f"⚠️ Failed with {encoding} encoding, trying next...")
                    continue
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error with {encoding}: {e}")
                    continue
            if file_clauses:
                clauses.extend(file_clauses)
                print(f"📄 Loaded {len(file_clauses)} clauses from {filename}")
            else:
                print(f"❌ Failed to load {filename} with any encoding")
        except FileNotFoundError:
            print(f"❌ File not found: {filename}")
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
    print(f"📋 Total clauses loaded: {len(clauses)}")
    if not clauses:
        print("⚠️ No clauses loaded! Check if JSON files exist and are valid.")
        print("💡 Make sure the files are in the correct directory and have valid JSON content.")
        print("🔧 Try running the PDF processing first to generate the JSON files.")
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
        try:
            print("🟢 inserting clause:", clause_data)
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
        except Exception as e:
            print(f"❌ Error inserting clause: {clause_data} - {e}")
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
    """
    30명 환자, 150~200건 청구, 다양한 진단명/상품/특약/날짜/승인비율, 현실적인 데이터 분포
    claim 상세내역, 보험금 산정, 통계/차트 모두 의미 있게 생성
    """
    fake = Faker('ko_KR')

    KOREAN_NAMES = [
        "김민수", "이서연", "박지훈", "최지우", "정민준", "김지민", "이준서", "박서연", "최현우", "정예린",
        "김하준", "이하은", "박지후", "최유진", "정서윤", "김도윤", "이도현", "박하린", "최지안", "정하은",
        "김시우", "이서진", "박지아", "최지호", "정지우", "김예준", "이하린", "박지민", "최서윤", "정하린"
    ]
    DIAGNOSES = [
        "급성 심근경색증", "위암", "유방암", "뇌졸중", "대장암", "폐암", "협심증", "뇌출혈", "간암", "신장암",
        "십이지장궤양", "고혈압", "관절염", "당뇨병", "부정맥", "기관지염", "폐렴", "골절", "탈구", "절상"
    ]
    HOSPITALS = [
        "서울아산병원", "삼성서울병원", "연세세브란스병원", "서울성모병원", "한양대학교병원", "고려대학교병원",
        "서울대학교병원", "경희대학교병원", "분당차병원", "부산대학교병원", "전남대학교병원", "충남대학교병원",
        "경북대학교병원", "전북대학교병원", "동네의원", "치과의원", "성형외과", "산부인과", "예방의학과", "피부과"
    ]
    TREATMENTS = ["입원치료", "수술", "통원치료"]
    STATUS_POOL = ["passed"] * 7 + ["failed"] * 3  # 7:3 비율

    patients = []
    for name in KOREAN_NAMES:
        ssn = fake.ssn()
        n_claims = random.randint(5, 7)
        for _ in range(n_claims):
            diagnosis = random.choice(DIAGNOSES)
            hospital = random.choice(HOSPITALS)
            treatment_type = random.choice(TREATMENTS)
            admission_days = random.randint(3, 15) if treatment_type == "입원치료" else 0
            medical_cost = random.randint(500_000, 3_000_000)
            status = random.choice(STATUS_POOL)
            # 날짜 분포: 최근 2년 내 월별 분산
            months_ago = random.randint(0, 23)
            diagnosis_date = (date.today().replace(day=1) - timedelta(days=months_ago*30)) + timedelta(days=random.randint(0, 27))
            patients.append({
                "name": name,
                "ssn": ssn,
                "diagnosis": diagnosis,
                "hospital": hospital,
                "treatment_type": treatment_type,
                "medical_cost": medical_cost,
                "admission_days": admission_days,
                "expected_amount": 0,  # 실제 산정은 claim 생성 시
                "status": status,
                "diagnosis_date": diagnosis_date
            })
    # 최일우 환자 1건(이미지와 1:1 매칭, failed)
    patients.append({
        "name": "최일우",
        "ssn": "000830-3381025",
        "address": "서울특별시 양천구 목동로 186 목동신시가지아파트7단지 734-1301",
        "phone": "010-9412-8362",
        "diagnosis": "우측 손목 척골 돌기부 손상 골절 및 삼각섬유 연골판 부분 파열",
        "hospital": "힘찬병원",
        "treatment_type": "입원치료",
        "medical_cost": 1200000,  # 예시 금액
        "admission_days": 7,      # 예시 입원일수
        "expected_amount": 0,
        "status": "failed",
        "diagnosis_date": date(2024, 5, 4),
        "doctor_name": "유순용",
        "icd_code": "S62.81"
        # receipt_items 없음 (보험금 지급 불가)
    })
    # 최일우 환자 6건 추가 (모두 passed, receipt_items 포함)
    passed_diagnoses = [
        ("골절", "입원치료", {"입원료": 1_000_000}),
        ("대장암", "수술", {"수술료": 1_500_000}),
        ("급성 심근경색증", "입원치료", {"입원료": 1_200_000}),
        ("위암", "수술", {"수술료": 2_000_000}),
        ("뇌졸중", "입원치료", {"입원료": 1_100_000}),
        ("암", "수술", {"수술료": 1_800_000, "검사료": 300_000})
    ]
    for i, (diagnosis, treatment_type, receipt_items) in enumerate(passed_diagnoses):
        months_ago = i
        diagnosis_date = (date.today().replace(day=1) - timedelta(days=months_ago*30)) + timedelta(days=random.randint(0, 27))
        patients.append({
            "name": "최일우",
            "ssn": "000830-3381025",
            "diagnosis": diagnosis,
            "hospital": "힘찬병원",
            "treatment_type": treatment_type,
            "medical_cost": sum(receipt_items.values()),
            "admission_days": random.randint(5, 15) if treatment_type == "입원치료" else 0,
            "expected_amount": 0,
            "status": "passed",
            "diagnosis_date": diagnosis_date,
            "receipt_items": receipt_items
        })
    random.shuffle(patients)
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
    """
    30명 환자, 150~200건 청구, 다양한 진단명/상품/특약/날짜/승인비율, 현실적인 데이터 분포
    claim 상세내역, 보험금 산정, 통계/차트 모두 의미 있게 생성
    """
    print("\n🏥 Creating medical and claim data for 30 patients...")
    patients = create_realistic_patients()
    user_ids = [1, 2, 3, 4, 5]  # 5명의 보험사 직원
    passed_count = 0
    failed_count = 0
    for i, patient_data in enumerate(patients, 1):
        print(f"\n👤 Creating patient {i}/{len(patients)}: {patient_data['name']} ({patient_data['status']})")
        # Create medical diagnosis
        diagnosis_date = patient_data["diagnosis_date"]
        doctor_name = f"Dr. {random.choice(['김의사', '이의사', '박의사', '최의사', '정의사'])}"
        icd_code = f"K{random.randint(10, 99)}.{random.randint(0, 9)}"
        diagnosis = MedicalDiagnosis(
            user_id=user_ids[i % 5],
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
        # Create UserContract (보험 가입 계약)
        product_choice = i % 3
        selected_product = products[product_choice]
        contract_number = f"CONTRACT-{patient_data['ssn'][:6]}-{i:03d}"
        start_date = diagnosis_date - timedelta(days=random.randint(30, 365))
        end_date = start_date + timedelta(days=365)
        premium_amounts = {"스마트보장보험": 50000, "실손의료비보장보험": 30000, "희망사랑보험": 80000}
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
        # 청구일: 영수증일 + 0~2일 랜덤, 시간/분/초 랜덤
        claim_created_at = datetime.combine(
            receipt.receipt_date + timedelta(days=random.randint(0, 2)),
            datetime.min.time()
        ) + timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        if patient_data["status"] == "passed":
            total_claim, matched_clauses, applied_clauses = match_and_calculate_realistic_clauses(patient_data, clause_objects)
            clause_details = [f"{c['clause_name']}: {c['amount']:,.2f}원" for c in applied_clauses]
            claim_reason = f"{patient_data['diagnosis']} 진단 및 치료 - " + ", ".join(clause_details)
            detailed_info = {
                "patient_subscriptions": matched_clauses,
                "matched_clauses": matched_clauses,
                "applied_clauses": applied_clauses,
                "calculation_basis": f"진단명: {patient_data['diagnosis']}, 치료방법: {patient_data['treatment_type']}, 입원일수: {patient_data['admission_days']}일",
                "subscription_status": "가입됨",
                "matching_status": "매칭됨"
            }
            claim_reason += f" | 상세내역: {json.dumps(detailed_info, ensure_ascii=False)}"
            print(f"  💰 Claim: {total_claim:,.2f}원")
            print(f"  📝 Applied clauses: {', '.join(matched_clauses)}")
            passed_count += 1
        else:
            total_claim = 0
            claim_reason = f"{patient_data['diagnosis']} - {patient_data.get('reason', '보장하지 않는 진료')}"
            detailed_info = {
                "patient_subscriptions": [],
                "matched_clauses": [],
                "applied_clauses": [],
                "calculation_basis": f"진단명: {patient_data['diagnosis']}, 치료방법: {patient_data['treatment_type']}",
                "subscription_status": "미가입",
                "matching_status": "미매칭",
                "failure_reason": patient_data.get('reason', '보장하지 않는 진료')
            }
            claim_reason += f" | 상세내역: {json.dumps(detailed_info, ensure_ascii=False)}"
            print(f"  ❌ Failed reason: {patient_data.get('reason', '보장하지 않는 진료')} - 청구 생성 (0원)")
            failed_count += 1
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
            created_at=claim_created_at
        )
        db.add(claim)
        db.commit()
    print(f"\n✅ Medical and claim data created successfully!")
    print(f"   - {len(patients)} Patients with medical cases")
    print(f"   - {passed_count} Passed cases (보험금 지급)")
    print(f"   - {failed_count} Failed cases (보험금 미지급)")
    print(f"   - {len(patients)} Diagnoses")
    print(f"   - {len(patients)} Receipts")
    print(f"   - {len(patients)} UserContracts (보험 가입 계약)")
    print(f"   - {len(patients)} Claims (all cases)")

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
        print("   - 30 Patients with medical cases")
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
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--init-only":
        # DB만 초기화
        init_database()
        print("✅ DB 스키마만 초기화 완료 (데이터 생성 없음)")
    else:
        main() 