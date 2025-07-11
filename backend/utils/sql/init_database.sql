-- 데이터베이스 초기화 스크립트 (Patient 테이블 없이 주민번호 기반)
-- 기존 테이블 삭제 (순서 주의)
DROP TABLE IF EXISTS forgery_analysis CASCADE;
DROP TABLE IF EXISTS claim_calculations CASCADE;
DROP TABLE IF EXISTS claims CASCADE;
DROP TABLE IF EXISTS medical_receipts CASCADE;
DROP TABLE IF EXISTS medical_diagnoses CASCADE;
DROP TABLE IF EXISTS user_subscriptions CASCADE;
DROP TABLE IF EXISTS user_contracts CASCADE;
DROP TABLE IF EXISTS insurance_clauses CASCADE;
DROP TABLE IF EXISTS insurance_products CASCADE;
DROP TABLE IF EXISTS insurance_companies CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 사용자 테이블 (보험사 직원)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 보험사 테이블
CREATE TABLE insurance_companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 보험 상품 테이블
CREATE TABLE insurance_products (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES insurance_companies(id),
    name VARCHAR(255) NOT NULL,
    product_code VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 보험 조항 테이블
CREATE TABLE insurance_clauses (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES insurance_products(id),
    clause_code VARCHAR(100) NOT NULL,
    clause_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    per_unit FLOAT NOT NULL,
    max_total FLOAT NOT NULL,
    unit_type VARCHAR(50) NOT NULL,
    description TEXT,
    conditions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 사용자 계약 테이블 (환자별 보험 계약 정보)
CREATE TABLE user_contracts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),  -- 보험사 직원 ID
    patient_name VARCHAR(255) NOT NULL,  -- 환자 이름
    patient_ssn VARCHAR(14) NOT NULL,  -- 환자 주민등록번호
    product_id INTEGER NOT NULL REFERENCES insurance_products(id),
    contract_number VARCHAR(255) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    premium_amount FLOAT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 사용자 가입 특약 테이블 (환자별 특약 가입 정보)
CREATE TABLE user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),  -- 보험사 직원 ID
    patient_name VARCHAR(255) NOT NULL,  -- 환자 이름
    patient_ssn VARCHAR(14) NOT NULL,  -- 환자 주민등록번호
    contract_id INTEGER NOT NULL REFERENCES user_contracts(id),
    clause_id INTEGER NOT NULL REFERENCES insurance_clauses(id),
    subscription_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 의료 진단서 테이블 (환자 정보 직접 저장)
CREATE TABLE medical_diagnoses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    patient_name VARCHAR(255) NOT NULL,
    patient_ssn VARCHAR(14) NOT NULL,  -- 주민등록번호 (필수)
    diagnosis_name VARCHAR(255) NOT NULL,
    diagnosis_date DATE NOT NULL,
    diagnosis_text TEXT NOT NULL,
    hospital_name VARCHAR(255) NOT NULL,
    doctor_name VARCHAR(255),
    icd_code VARCHAR(50),
    admission_days INTEGER DEFAULT 0,
    image_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 의료 영수증 테이블 (환자 정보 직접 저장)
CREATE TABLE medical_receipts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    patient_name VARCHAR(255) NOT NULL,
    -- patient_ssn 제거 - 영수증에는 주민번호가 없음, 진단서를 통해 환자 식별
    receipt_date DATE NOT NULL,
    total_amount FLOAT NOT NULL,
    hospital_name VARCHAR(255) NOT NULL,
    treatment_details TEXT,
    image_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 보험금 청구 테이블 (환자 정보 직접 저장)
CREATE TABLE claims (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    patient_name VARCHAR(255) NOT NULL,
    patient_ssn VARCHAR(14) NOT NULL,  -- 주민등록번호 (필수)
    diagnosis_id INTEGER NOT NULL REFERENCES medical_diagnoses(id),
    receipt_id INTEGER NOT NULL REFERENCES medical_receipts(id),
    claim_amount FLOAT NOT NULL,
    claim_reason TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 청구 계산 테이블
CREATE TABLE claim_calculations (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES claims(id),
    clause_id INTEGER NOT NULL REFERENCES insurance_clauses(id),
    calculated_amount FLOAT NOT NULL,
    calculation_logic TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 위조 분석 테이블
CREATE TABLE forgery_analysis (
    id SERIAL PRIMARY KEY,
    diagnosis_id INTEGER NOT NULL REFERENCES medical_diagnoses(id),
    receipt_id INTEGER NOT NULL REFERENCES medical_receipts(id),
    analysis_result TEXT NOT NULL,
    confidence_score FLOAT,
    fraud_indicators TEXT,
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 인덱스 생성
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_insurance_companies_code ON insurance_companies(code);
CREATE INDEX idx_insurance_products_company_id ON insurance_products(company_id);
CREATE INDEX idx_insurance_clauses_product_id ON insurance_clauses(product_id);
CREATE INDEX idx_medical_diagnoses_user_id ON medical_diagnoses(user_id);
CREATE INDEX idx_medical_diagnoses_patient_ssn ON medical_diagnoses(patient_ssn);  -- 주민번호 인덱스
CREATE INDEX idx_medical_receipts_user_id ON medical_receipts(user_id);
-- 영수증 테이블에는 주민번호가 없으므로 인덱스 제거
CREATE INDEX idx_claims_user_id ON claims(user_id);
CREATE INDEX idx_claims_patient_ssn ON claims(patient_ssn);  -- 주민번호 인덱스
CREATE INDEX idx_claims_diagnosis_id ON claims(diagnosis_id);
CREATE INDEX idx_claims_receipt_id ON claims(receipt_id);
CREATE INDEX idx_user_contracts_patient_ssn ON user_contracts(patient_ssn);  -- 환자 주민번호 인덱스
CREATE INDEX idx_user_subscriptions_patient_ssn ON user_subscriptions(patient_ssn);  -- 환자 주민번호 인덱스

-- 시스템 사용자 생성
INSERT INTO users (id, email, name, password) VALUES 
(1, 'system@insurance.com', 'System User', 'hashed_password_here');

COMMIT; 