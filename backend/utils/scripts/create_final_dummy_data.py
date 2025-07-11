#!/usr/bin/env python3
"""
Final Dummy Data Creation Script
Includes DB initialization and comprehensive patient data using extracted clauses
"""

import sys
import os
import json

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
from datetime import datetime, date, timedelta
import random

# Database URL
DATABASE_URL = "postgresql://postgres:postgres123@postgres:5432/insurance_system"

def init_database():
    """Initialize database with fresh schema"""
    print("🔄 Initializing database...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Drop all tables and recreate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialized successfully!")
    return engine

def load_extracted_clauses():
    """Load extracted insurance clauses from JSON files"""
    clauses = []
    
    # Load clauses from all three insurance products
    # Path adjusted for new script location
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
    """Create sample users (insurance company employees)"""
    print("\n👥 Creating users...")
    
    # 비밀번호 해싱을 위한 import
    from utils.auth import get_password_hash
    
    users_data = [
        {"email": "admin@samsung.com", "name": "관리자", "password": "admin123"},
        {"email": "agent1@samsung.com", "name": "김보험", "password": "agent123"},
        {"email": "agent2@samsung.com", "name": "이청구", "password": "agent123"},
        {"email": "manager@samsung.com", "name": "박매니저", "password": "manager123"},
    ]
    
    for user_data in users_data:
        # 비밀번호 해싱
        hashed_password = get_password_hash(user_data["password"])
        
        user = User(
            email=user_data["email"],
            name=user_data["name"],
            password=hashed_password
        )
        db.add(user)
        print(f"  👤 Created user: {user_data['name']} ({user_data['email']})")
    
    db.commit()
    print("✅ Users created successfully!")

def create_insurance_data(db):
    """Create insurance companies, products, and clauses from extracted data"""
    print("\n🏢 Creating insurance data...")
    
    # Load extracted clauses
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
        if "실손" in clause_data.get("category", "") or "입원의료비" in clause_data.get("category", "") or "외래진료" in clause_data.get("category", "") or "담보" in clause_data.get("clause_name", ""):
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

def create_medical_and_claim_data(db, clause_objects, products):
    """Create medical diagnoses, receipts, and claims"""
    print("\n🏥 Creating medical and claim data...")
    
    # 최일우 보험 가입 정보만 생성 (진단서/영수증은 나중에 이미지 처리로 생성)
    print("\n👤 Creating insurance subscription for 최일우...")
    
    # 최일우의 보험 계약 생성 (실손의료비보장보험)
    choi_contract = UserContract(
        user_id=1,  # 관리자가 처리
        patient_name="최일우",
        patient_ssn="000830-3381025",
        product_id=products[1].id,  # 실손의료비보장보험
        contract_number="CHOI-2024-001",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
        premium_amount=50000,
        status="active"
    )
    db.add(choi_contract)
    db.commit()
    db.refresh(choi_contract)
    
    # 최일우가 가입한 특약들 (골절 관련) - 총 50,000원 보험금
    choi_clause_names = ["상해통원담보", "질병진단특약", "진단검사특약"]
    for clause_name in choi_clause_names:
        clause = next((c for c in clause_objects if c.clause_name == clause_name), None)
        if clause:
            subscription = UserSubscription(
                user_id=1,  # 관리자가 처리
                patient_name="최일우",
                patient_ssn="000830-3381025",
                contract_id=choi_contract.id,
                clause_id=clause.id,
                subscription_date=date(2024, 1, 1),
                status="active"
            )
            db.add(subscription)
            print(f"  📋 Added subscription: {clause_name}")
    
    db.commit()
    
    # 최일우 특약 금액을 현실적으로 조정 (총 50,000원)
    print("🔧 최일우 특약 금액 조정 중...")
    
    # 최일우가 가입한 특약들의 금액을 수정
    choi_clause_updates = {
        "상해통원담보": {"per_unit": 20000, "max_total": 20000},
        "질병진단특약": {"per_unit": 15000, "max_total": 15000},
        "진단검사특약": {"per_unit": 15000, "max_total": 15000}
    }
    
    for clause_name, amounts in choi_clause_updates.items():
        clause = next((c for c in clause_objects if c.clause_name == clause_name), None)
        if clause:
            clause.per_unit = amounts["per_unit"]
            clause.max_total = amounts["max_total"]
            db.add(clause)
            print(f"  💰 Updated {clause_name}: {amounts['per_unit']:,}원")
    
    db.commit()
    print("✅ 최일우 보험 가입 정보 생성 완료! (총 예상 보험금: 50,000원)")
    
    # 나머지 5명 환자들의 의료 데이터 생성
    patients_data = [
        {
            "name": "김태수",
            "ssn": "850315-1234567",
            "phone": "010-1234-5678",
            "address": "서울시 강남구 역삼동 123-45",
            "diagnosis": "급성 심근경색증",
            "hospital": "서울아산병원",
            "treatment_type": "입원치료",
            "medical_cost": 2500000,
            "admission_days": 7,
            "relevant_clauses": ["질병입원담보", "입원특약"],  # 현실적인 보험금: 7일 × 50,000원 = 350,000원
            "create_claim": True
        },
        {
            "name": "오유민", 
            "ssn": "920728-2345678",
            "phone": "010-2345-6789",
            "address": "서울시 서초구 방배동 234-56",
            "diagnosis": "유방암",
            "hospital": "삼성서울병원",
            "treatment_type": "수술",
            "medical_cost": 5000000,
            "admission_days": 14,
            "relevant_clauses": ["암진단특약", "암직접치료입원특약"],  # 현실적인 보험금: 1,000,000원 + (14일 × 50,000원) = 1,700,000원
            "create_claim": True
        },
        {
            "name": "임윤환",
            "ssn": "780612-1345678", 
            "phone": "010-3456-7890",
            "address": "서울시 마포구 홍대동 345-67",
            "diagnosis": "당뇨병성 신증",
            "hospital": "연세세브란스병원",
            "treatment_type": "통원치료",
            "medical_cost": 150000,
            "admission_days": 0,
            "relevant_clauses": ["질병통원담보", "처방조제비담보"],  # 현실적인 보험금: 50,000원 + 100,000원 = 150,000원
            "create_claim": True
        },
        {
            "name": "김다현",
            "ssn": "950403-2456789",
            "phone": "010-4567-8901",
            "address": "서울시 송파구 잠실동 456-78",
            "diagnosis": "폐렴",
            "hospital": "서울성모병원",
            "treatment_type": "입원치료",
            "medical_cost": 800000,
            "admission_days": 5,
            "relevant_clauses": ["질병입원담보", "입원특약"],  # 현실적인 보험금: 5일 × 50,000원 × 2 = 500,000원
            "create_claim": True
        },
        {
            "name": "김수현",
            "ssn": "881120-1567890",
            "phone": "010-5678-9012",
            "address": "서울시 영등포구 여의도동 567-89", 
            "diagnosis": "교통사고로 인한 다발성 골절",
            "hospital": "한양대학교병원",
            "treatment_type": "수술",
            "medical_cost": 3200000,
            "admission_days": 21,
            "relevant_clauses": ["상해입원담보"],  # 현실적인 보험금: 21일 × 50,000원 = 1,050,000원
            "create_claim": True
        }
    ]
    
    # Create patients and their medical/claim data
    for i, patient_data in enumerate(patients_data, 1):
        print(f"\n👤 Creating patient {i}/5: {patient_data['name']}")
        
        # Create medical diagnosis
        diagnosis_date = date.today() - timedelta(days=random.randint(1, 30))
        doctor_name = f"Dr. {random.choice(['김의사', '이의사', '박의사', '최의사'])}"
        icd_code = f"K{random.randint(10, 99)}.{random.randint(0, 9)}"
        
        diagnosis = MedicalDiagnosis(
            user_id=1,  # 관리자가 등록
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
            user_id=1,  # 관리자가 등록
            patient_name=patient_data["name"],
            receipt_date=receipt_date,
            hospital_name=patient_data["hospital"],
            total_amount=patient_data["medical_cost"],
            treatment_details=treatment_details
        )
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        
        print(f"  📋 Diagnosis: {patient_data['diagnosis']}")
        print(f"  🧾 Receipt: {patient_data['medical_cost']:,}원")
        
        # 모든 환자에 대해 청구 생성 (최일우 제외됨)
        if patient_data["create_claim"]:
            # Calculate claim amount based on relevant clauses
            claim_amount = 0
            claim_reason_parts = []
            
            for clause_name in patient_data["relevant_clauses"]:
                clause = next((c for c in clause_objects if c.clause_name == clause_name), None)
                if clause:
                    if clause.unit_type == "amount":
                        if "입원" in clause.clause_name and patient_data["admission_days"] > 0:
                            # Per day payment for hospitalization
                            amount = clause.per_unit * patient_data["admission_days"]
                            claim_amount += min(amount, clause.max_total)
                            claim_reason_parts.append(f"{clause.clause_name} ({patient_data['admission_days']}일)")
                        elif "진단" in clause.clause_name:
                            # One-time payment for diagnosis
                            claim_amount += clause.per_unit
                            claim_reason_parts.append(f"{clause.clause_name} (진단)")
                        elif "수술" in clause.clause_name and patient_data["treatment_type"] == "수술":
                            # One-time payment for surgery
                            claim_amount += clause.per_unit
                            claim_reason_parts.append(f"{clause.clause_name} (수술)")
                        elif "통원" in clause.clause_name and patient_data["treatment_type"] == "통원치료":
                            # Payment for outpatient treatment
                            claim_amount += clause.per_unit
                            claim_reason_parts.append(f"{clause.clause_name} (통원)")
                        elif "담보" in clause.clause_name:
                            # For 실손보험 clauses, use actual medical cost minus deductible
                            claim_amount += min(clause.per_unit, patient_data["medical_cost"])
                            claim_reason_parts.append(f"{clause.clause_name} (실손)")
                        else:
                            # General treatment coverage
                            claim_amount += clause.per_unit
                            claim_reason_parts.append(clause.clause_name)
            
            claim_reason = f"{patient_data['diagnosis']} 진단 및 치료 - " + ", ".join(claim_reason_parts)
            
            # Create claim
            claim = Claim(
                user_id=1,  # 관리자가 처리
                patient_name=patient_data["name"],
                patient_ssn=patient_data["ssn"],
                diagnosis_id=diagnosis.id,
                receipt_id=receipt.id,
                claim_amount=claim_amount,
                claim_reason=claim_reason,
                status="pending",
                created_at=datetime.utcnow()
            )
            db.add(claim)
            db.commit()
            
            print(f"  💰 Claim: {claim_amount:,}원")
            print(f"  📝 Applied clauses: {', '.join(patient_data['relevant_clauses'])}")

    
    print("\n✅ Medical and claim data created successfully!")
    print(f"   - 5 Patients with medical cases")
    print(f"   - 5 Diagnoses")
    print(f"   - 5 Receipts")
    print(f"   - 5 Claims")
    print(f"   - 최일우: 보험 가입 정보만 등록, 진단서/영수증은 이미지 처리로 생성 예정")

def main():
    """Main function to create all dummy data"""
    print("🚀 Starting Final Dummy Data Creation with Extracted Clauses...")
    
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
        
        print("\n🎉 All dummy data created successfully!")
        print("\n📊 Summary:")
        print("   - 4 Users (insurance employees)")
        print("   - 1 Insurance Company (삼성생명)")
        print("   - 3 Insurance Products")
        print(f"   - {len(clause_objects)} Insurance Clauses (from extracted data)")
        print("   - 최일우: 보험 가입 정보 (계약 + 특약)")
        print("   - 5 Patients with complete medical records")
        print("   - 5 Medical Diagnoses")
        print("   - 5 Medical Receipts")
        print("   - 5 Claims")
        
        print("\n🔗 API Testing:")
        print("   - POST /v1/medical/diagnoses - 진단서 등록")
        print("   - POST /v1/medical/receipts - 영수증 등록")
        print("   - POST /v1/claims/create - 보험금 청구")
        print("   - GET /v1/claims/user-claims?patient_ssn=000830-3381025 - 최일우 청구 조회")
        print("   - GET /v1/claims/all-claims - 전체 청구 조회")
        
    except Exception as e:
        print(f"❌ Error creating dummy data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main() 