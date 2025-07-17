from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships (보험사 직원으로서 처리한 업무들)
    diagnoses = relationship("MedicalDiagnosis", back_populates="user")
    receipts = relationship("MedicalReceipt", back_populates="user")
    claims = relationship("Claim", back_populates="user")

class InsuranceCompany(Base):
    __tablename__ = "insurance_companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)  # 활성화 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    products = relationship("InsuranceProduct", back_populates="company")

class InsuranceProduct(Base):
    __tablename__ = "insurance_products"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("insurance_companies.id"), nullable=False)
    name = Column(String, nullable=False)
    product_code = Column(String, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)  # 활성화 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    company = relationship("InsuranceCompany", back_populates="products")
    clauses = relationship("InsuranceClause", back_populates="product")

class InsuranceClause(Base):
    __tablename__ = "insurance_clauses"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("insurance_products.id"), nullable=False)
    clause_code = Column(String, nullable=False)
    clause_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    per_unit = Column(Float, nullable=False)
    max_total = Column(Float, nullable=False)
    unit_type = Column(String, nullable=False)  # 'percentage' or 'amount'
    description = Column(Text)
    conditions = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    product = relationship("InsuranceProduct", back_populates="clauses")
    calculations = relationship("ClaimCalculation", back_populates="clause")

class MedicalDiagnosis(Base):
    __tablename__ = "medical_diagnoses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 보험사 직원 ID
    patient_name = Column(String, nullable=False)  # 피보험자 이름
    patient_ssn = Column(String, nullable=False)  # 피보험자 주민등록번호 (필수)
    diagnosis_name = Column(String, nullable=False)  # 진단명
    diagnosis_date = Column(Date, nullable=False)
    diagnosis_text = Column(Text, nullable=False)
    hospital_name = Column(String, nullable=False)
    doctor_name = Column(String)
    icd_code = Column(String)
    admission_days = Column(Integer, default=0)  # 입원일수
    # 이미지 URL
    image_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="diagnoses")  # 처리한 보험사 직원
    claims = relationship("Claim", back_populates="diagnosis")

class MedicalReceipt(Base):
    __tablename__ = "medical_receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 보험사 직원 ID
    patient_name = Column(String, nullable=False)  # 피보험자 이름
    # patient_ssn 제거 - 영수증에는 주민번호가 없음, 진단서를 통해 환자 식별
    receipt_date = Column(Date, nullable=False)
    total_amount = Column(Float, nullable=False)
    hospital_name = Column(String, nullable=False)
    treatment_details = Column(Text)
    # 이미지 URL
    image_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="receipts")  # 처리한 보험사 직원
    claims = relationship("Claim", back_populates="receipt")

class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 보험사 직원 ID
    patient_name = Column(String, nullable=False)  # 피보험자 이름
    patient_ssn = Column(String, nullable=False)  # 피보험자 주민등록번호 (필수)
    diagnosis_id = Column(Integer, ForeignKey("medical_diagnoses.id"), nullable=False)
    receipt_id = Column(Integer, ForeignKey("medical_receipts.id"), nullable=False)
    claim_amount = Column(Float, nullable=False)
    claim_reason = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected, paid
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="claims")  # 처리한 보험사 직원
    diagnosis = relationship("MedicalDiagnosis", back_populates="claims")
    receipt = relationship("MedicalReceipt", back_populates="claims")
    calculations = relationship("ClaimCalculation", back_populates="claim")

class ClaimCalculation(Base):
    __tablename__ = "claim_calculations"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    clause_id = Column(Integer, ForeignKey("insurance_clauses.id"), nullable=False)
    calculated_amount = Column(Float, nullable=False)
    calculation_logic = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    claim = relationship("Claim", back_populates="calculations")
    clause = relationship("InsuranceClause", back_populates="calculations")

class UserContract(Base):
    __tablename__ = "user_contracts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 보험사 직원 ID
    patient_name = Column(String, nullable=False)  # 환자 이름
    patient_ssn = Column(String, nullable=False)  # 환자 주민등록번호
    product_id = Column(Integer, ForeignKey("insurance_products.id"), nullable=False)
    contract_number = Column(String, unique=True, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    premium_amount = Column(Float, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User")  # 처리한 보험사 직원
    product = relationship("InsuranceProduct")
    subscriptions = relationship("UserSubscription", back_populates="contract")

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 보험사 직원 ID
    patient_name = Column(String, nullable=False)  # 환자 이름
    patient_ssn = Column(String, nullable=False)  # 환자 주민등록번호
    contract_id = Column(Integer, ForeignKey("user_contracts.id"), nullable=False)
    clause_id = Column(Integer, ForeignKey("insurance_clauses.id"), nullable=False)
    subscription_date = Column(Date, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User")  # 처리한 보험사 직원
    contract = relationship("UserContract", back_populates="subscriptions")
    clause = relationship("InsuranceClause")

class ForgeryAnalysis(Base):
    __tablename__ = "forgery_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    diagnosis_id = Column(Integer, ForeignKey("medical_diagnoses.id"), nullable=True)
    receipt_id = Column(Integer, ForeignKey("medical_receipts.id"), nullable=True)
    analysis_result = Column(String, nullable=False)  # "forged" or "authentic"
    confidence_score = Column(Float)
    fraud_indicators = Column(Text)
    analysis_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    diagnosis = relationship("MedicalDiagnosis")
    receipt = relationship("MedicalReceipt") 