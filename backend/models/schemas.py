from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Insurance schemas
class InsuranceClauseBase(BaseModel):
    clause_code: str
    clause_name: str
    category: str
    per_unit: float
    max_total: float
    unit_type: str
    description: Optional[str] = None
    conditions: Optional[str] = None

class InsuranceClauseCreate(InsuranceClauseBase):
    product_id: int

class InsuranceClauseResponse(InsuranceClauseBase):
    id: int
    product_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Medical schemas
class MedicalDiagnosisBase(BaseModel):
    patient_name: str  # 진단서에 있는 고객 이름
    patient_ssn: str  # 주민등록번호 (필수)
    diagnosis_date: date
    diagnosis_text: str
    hospital_name: str
    doctor_name: Optional[str] = None
    icd_code: Optional[str] = None

class MedicalDiagnosisCreate(BaseModel):
    patient_name: str
    patient_ssn: str  # 주민등록번호 (필수)
    diagnosis_name: str
    diagnosis_date: date
    diagnosis_text: Optional[str] = None  # 진단 상세 내용
    icd_code: Optional[str] = None
    hospital_name: str
    doctor_name: Optional[str] = None
    admission_days: Optional[int] = 0

class MedicalDiagnosisResponse(MedicalDiagnosisBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class MedicalReceiptBase(BaseModel):
    patient_name: str  # 영수증에 있는 고객 이름
    receipt_date: date
    total_amount: float
    hospital_name: str
    treatment_details: Optional[str] = None

class MedicalReceiptCreate(BaseModel):
    patient_name: str
    receipt_date: date
    total_amount: float
    hospital_name: str
    treatment_details: Optional[str] = None

class MedicalReceiptResponse(MedicalReceiptBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Claim schemas
class ClaimBase(BaseModel):
    diagnosis_id: int
    receipt_id: int
    claim_reason: Optional[str] = None

class ClaimCreate(ClaimBase):
    user_id: int

class ClaimResponse(ClaimBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ClaimCalculationBase(BaseModel):
    clause_id: int
    calculated_amount: float
    calculation_logic: Optional[str] = None

class ClaimCalculationResponse(ClaimCalculationBase):
    id: int
    claim_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None 