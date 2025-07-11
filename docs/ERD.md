# 🏗️ ERD Cloud 스키마 정의

## ERD Cloud 입력용 스키마

### 테이블 정의

```sql
-- 보험사 직원 테이블
users {
  id integer pk increments                  -- 사용자 고유 ID
  email varchar(255) unique not null        -- 이메일 (로그인 ID)
  name varchar(255) not null                -- 직원 이름
  password varchar(255) not null            -- 비밀번호 (해시 처리)
  created_at timestamp with time zone default current_timestamp  -- 계정 생성일
  updated_at timestamp with time zone default current_timestamp  -- 수정일
  is_deleted boolean default false          -- 소프트 삭제 플래그
}

-- 보험사 테이블
insurance_companies {
  id integer pk increments                  -- 보험사 고유 ID
  name varchar(255) not null                -- 보험사 이름 (예: 삼성생명)
  code varchar(100) unique not null        -- 보험사 코드 (예: SAMSUNG_LIFE)
  is_active boolean default true           -- 보험사 활성화 상태
  created_at timestamp default now()        -- 등록일
  is_deleted boolean default false          -- 소프트 삭제 플래그
}

-- 보험 상품 테이블
insurance_products {
  id integer pk increments                  -- 보험상품 고유 ID
  company_id integer fk > insurance_companies.id  -- 보험사 참조 ID
  name varchar(255) not null                -- 상품명 (예: 스마트보장보험)
  product_code varchar(100) not null       -- 상품 코드 (예: SMART_PROTECTION)
  description text                          -- 상품 설명
  is_active boolean default true           -- 상품 활성화 상태
  created_at timestamp default now()        -- 상품 등록일
  is_deleted boolean default false          -- 소프트 삭제 플래그
}

-- 보험 조항 테이블 (실손의료비, 수술비 등)
insurance_clauses {
  id integer pk increments                  -- 보험조항 고유 ID
  product_id integer fk > insurance_products.id  -- 보험상품 참조 ID
  clause_code varchar(100) not null        -- 조항 코드 (예: CL001)
  clause_name varchar(255) not null        -- 조항명 (예: 실손의료비담보)
  category varchar(100) not null           -- 조항 카테고리 (예: 실손의료비)
  per_unit float not null                  -- 단위당 보험금 (예: 80% 또는 50만원)
  max_total float not null                 -- 최대 보험금 한도
  unit_type varchar(50) not null          -- 단위 유형 (percentage/fixed/daily)
  description text                         -- 조항 상세 설명
  conditions text                          -- 적용 조건 (예: 입원 3일 이상)
  created_at timestamp default now()       -- 조항 등록일
  is_deleted boolean default false         -- 소프트 삭제 플래그
}

-- 환자 계약 정보 테이블
user_contracts {
  id integer pk increments                  -- 계약 고유 ID
  user_id integer fk > users.id            -- 담당 직원 ID
  patient_name varchar(255) not null       -- 환자 이름
  patient_ssn varchar(14) not null         -- 환자 주민번호 (123456-1234567)
  product_id integer fk > insurance_products.id  -- 가입 보험상품 ID
  contract_number varchar(255) unique not null   -- 계약번호 (예: CHOI-2024-001)
  start_date date not null                 -- 계약 시작일
  end_date date not null                   -- 계약 만료일
  premium_amount float not null            -- 월 보험료
  status varchar(50) default 'active'     -- 계약 상태 (active/expired/cancelled)
  created_at timestamp default now()       -- 계약 등록일
  is_deleted boolean default false         -- 소프트 삭제 플래그
}

-- 환자별 특약 가입 정보
user_subscriptions {
  id integer pk increments                  -- 특약가입 고유 ID
  user_id integer fk > users.id            -- 담당 직원 ID
  patient_name varchar(255) not null       -- 환자 이름
  patient_ssn varchar(14) not null         -- 환자 주민번호
  contract_id integer fk > user_contracts.id  -- 기본 계약 참조 ID
  clause_id integer fk > insurance_clauses.id  -- 가입한 특약 조항 ID
  subscription_date date not null          -- 특약 가입일
  status varchar(50) default 'active'     -- 특약 상태 (active/expired/cancelled)
  created_at timestamp default now()       -- 특약 등록일
  is_deleted boolean default false         -- 소프트 삭제 플래그
}

-- 의료 진단서 테이블
medical_diagnoses {
  id integer pk increments                  -- 진단서 고유 ID
  user_id integer fk > users.id            -- 등록한 직원 ID
  patient_name varchar(255) not null       -- 환자 이름
  patient_ssn varchar(14) not null         -- 환자 주민번호 (필수)
  diagnosis_name varchar(255) not null     -- 진단명 (예: 급성 맹장염)
  diagnosis_date date not null             -- 진단일
  diagnosis_text text not null             -- 진단 내용 상세
  hospital_name varchar(255) not null      -- 병원명
  doctor_name varchar(255)                 -- 담당의사명 (선택사항)
  icd_code varchar(50)                     -- ICD-10 질병코드 (선택사항)
  admission_days integer default 0         -- 입원일수 (0=외래)
  image_url varchar(500)                   -- 진단서 이미지 파일 경로
  created_at timestamp default now()       -- 진단서 등록일
  is_deleted boolean default false         -- 소프트 삭제 플래그
}

-- 의료 영수증 테이블
medical_receipts {
  id integer pk increments                  -- 영수증 고유 ID
  user_id integer fk > users.id            -- 등록한 직원 ID
  patient_name varchar(255) not null       -- 환자 이름
  -- patient_ssn 제거: 영수증에는 주민번호가 없음, 진단서를 통해 환자 식별
  receipt_date date not null               -- 영수증 발급일
  total_amount float not null              -- 총 치료비
  hospital_name varchar(255) not null      -- 병원명
  treatment_details text                   -- 치료 내역 상세
  image_url varchar(500)                   -- 영수증 이미지 파일 경로
  created_at timestamp default now()       -- 영수증 등록일
  is_deleted boolean default false         -- 소프트 삭제 플래그
}

-- 보험금 청구 테이블
claims {
  id integer pk increments                  -- 청구 고유 ID
  user_id integer fk > users.id            -- 처리 담당 직원 ID
  patient_name varchar(255) not null       -- 환자 이름
  patient_ssn varchar(14) not null         -- 환자 주민번호 (필수)
  diagnosis_id integer fk > medical_diagnoses.id  -- 진단서 참조 ID
  receipt_id integer fk > medical_receipts.id     -- 영수증 참조 ID
  claim_amount float not null              -- 청구 보험금 (영수증의 총금액을 기반으로 계산)
  claim_reason text not null               -- 청구 사유
  status varchar(50) default 'pending'    -- 청구 상태 (pending/approved/rejected)
  created_at timestamp default now()       -- 청구 신청일
  is_deleted boolean default false         -- 소프트 삭제 플래그
}

-- 청구 계산 상세 테이블
claim_calculations {
  id integer pk increments                  -- 계산 고유 ID
  claim_id integer fk > claims.id          -- 청구 참조 ID
  clause_id integer fk > insurance_clauses.id  -- 적용된 보험조항 ID
  calculated_amount float not null         -- 해당 조항으로 계산된 보험금
  calculation_logic text                   -- 계산 과정 설명 (80% 적용 등)
  created_at timestamp default now()       -- 계산 실행일
  is_deleted boolean default false         -- 소프트 삭제 플래그
}

-- 위조 분석 테이블
forgery_analysis {
  id integer pk increments                  -- 분석 고유 ID
  diagnosis_id integer fk > medical_diagnoses.id  -- 진단서 참조 ID
  receipt_id integer fk > medical_receipts.id     -- 영수증 참조 ID
  analysis_result text not null            -- 분석 결과 (정상/의심/위조)
  confidence_score float                   -- 신뢰도 점수 (0.0-1.0)
  fraud_indicators text                    -- 위조 의심 요소들
  analysis_date timestamp default now()    -- 분석 실행일
  is_deleted boolean default false         -- 소프트 삭제 플래그
}
```

## 📊 테이블 관계 요약

### 🔗 **Primary Key (PK) & Foreign Key (FK) 관계도**

```
┌─────────────────────┐
│      users          │ 🏢 보험사 직원
│  PK: id             │
│  UK: email          │
└─────────────────────┘
          │
          ├─────────────────────────────────────────────────────┐
          │                                                     │
          ▼                                                     ▼
┌─────────────────────┐                              ┌─────────────────────┐
│ medical_diagnoses   │ 📋 진단서                    │ medical_receipts    │ 🧾 영수증
│  PK: id             │                              │  PK: id             │
│  FK: user_id        │◄─────────────────────────────│  FK: user_id        │
│  IDX: patient_ssn   │                              │  patient_name       │
└─────────────────────┘                              └─────────────────────┘
          │                                                     │
          └─────────────────────┐       ┌─────────────────────────┘
                                │       │
                                ▼       ▼
                        ┌─────────────────────┐
                        │      claims         │ 💰 보험금 청구
                        │  PK: id             │
                        │  FK: user_id        │
                        │  FK: diagnosis_id   │
                        │  FK: receipt_id     │
                        │  IDX: patient_ssn   │
                        └─────────────────────┘
                                │
                                ▼
                        ┌─────────────────────┐
                        │ claim_calculations  │ 🧮 계산 상세
                        │  PK: id             │
                        │  FK: claim_id       │
                        │  FK: clause_id      │
                        └─────────────────────┘
                                │
                                ▼
                        ┌─────────────────────┐
                        │ insurance_clauses   │ 📜 보험 조항
                        │  PK: id             │
                        │  FK: product_id     │
                        └─────────────────────┘
                                │
                                ▼
                        ┌─────────────────────┐
                        │ insurance_products  │ 📦 보험 상품
                        │  PK: id             │
                        │  FK: company_id     │
                        └─────────────────────┘
                                │
                                ▼
                        ┌─────────────────────┐
                        │ insurance_companies │ 🏢 보험사
                        │  PK: id             │
                        │  UK: code           │
                        └─────────────────────┘
```

### 🏥 **환자 계약 관계**
```
┌─────────────────────┐
│      users          │ 🏢 보험사 직원
│  PK: id             │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  user_contracts     │ 📋 환자 계약
│  PK: id             │
│  FK: user_id        │
│  FK: product_id     │
│  UK: contract_number│
│  IDX: patient_ssn   │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│ user_subscriptions  │ ✅ 특약 가입
│  PK: id             │
│  FK: user_id        │
│  FK: contract_id    │
│  FK: clause_id      │
│  IDX: patient_ssn   │
└─────────────────────┘
```

### 🔍 **위조 분석 관계 (1:N)**
```
┌─────────────────────┐    ┌─────────────────────┐
│ medical_diagnoses   │    │ medical_receipts    │
│  PK: id             │    │  PK: id             │
└─────────────────────┘    └─────────────────────┘
          │ 1                      │ 1
          │                        │
          │    ┌─────────────────────┐
          └────┤  forgery_analysis   │ 🔍 위조 분석
               │  PK: id             │ N
               │  FK: diagnosis_id   │
               │  FK: receipt_id     │ N
               └─────────────────────┘
                        │
                        └─────────────┘

💡 **1:N 관계 이유**
- 하나의 진단서는 여러 번 위조분석 가능 (재검토)
- 하나의 영수증은 여러 번 위조분석 가능 (재검토)
- 같은 문서 조합도 시간에 따라 다시 분석 가능
```

### 🏢 **보험사 구조**
```
insurance_companies (보험사)
  ↳ insurance_products (보험상품)
    ↳ insurance_clauses (보험조항)
```

### 👥 **사용자 & 계약**
```
users (보험사 직원)
  ↳ user_contracts (환자 계약)
    ↳ user_subscriptions (특약 가입)
```

### 🏥 **의료 정보**
```
users (보험사 직원)
  ↳ medical_diagnoses (진단서)
  ↳ medical_receipts (영수증)
```

### 💰 **청구 처리**
```
claims (보험금 청구)
  ├── medical_diagnoses (진단서 참조)
  ├── medical_receipts (영수증 참조)
  └── claim_calculations (계산 상세)
    └── insurance_clauses (적용 조항)
```

### 🔍 **분석 시스템**
```
forgery_analysis (위조 분석)
  ├── medical_diagnoses (진단서 분석)
  └── medical_receipts (영수증 분석)
```

## 🔑 주요 특징

### 1. **환자 정보 저장 방식**
- **`patient_ssn` (환자 주민번호)**: 
  - 진단서, 청구에는 **필수** (의료진이 신원 확인 후 발급)
  - 영수증에는 **없음** (실제 영수증에는 주민번호 없음, 진단서를 통해 환자 식별)
- **`patient_name` (환자명)**: 모든 테이블에 중복 저장 (매칭 및 검색 용이성)

### 2. **보험금 계산 로직**
- **`insurance_clauses.unit_type`**: 
  - `percentage`: 치료비의 %로 계산 (예: 80%)
  - `fixed`: 정액 지급 (예: 50만원)
  - `daily`: 일당 지급 (예: 입원일수 × 5만원)
- **`per_unit`**: 단위당 보험금 (80, 500000, 50000 등)
- **`max_total`**: 최대 지급 한도

### 3. **관계 설정**
- **`FK` (Foreign Key)**: 필수 참조 관계
- **`nullable`**: 선택적 관계 (일부 필드만 해당)
- **`unique`**: 중복 방지 (이메일, 계약번호 등)

### 4. **소프트 삭제 정책**
- 모든 테이블에 **`is_deleted`** 플래그 적용
- 실제 데이터는 삭제하지 않고 플래그만 변경
- 감사 추적 및 데이터 복구 가능

### 5. **이미지 파일 관리**
- **`image_url`**: 서버 내 파일 경로 저장
- 진단서: `backend/uploads/diagnosis/`
- 영수증: `backend/uploads/receipts/`

### 6. **실제 데이터 예시**
- **환자**: 최일우 (000830-3381025)
- **보험상품**: 실손의료비보장보험
- **특약**: 상해통원담보, 질병진단특약, 진단검사특약
- **진단**: 급성 맹장염, 입원 3일
- **보험금**: 실손의료비 80% + 수술비 정액 + 입원비 일당

### 7. **인덱스 설계**
```sql
-- 성능 최적화를 위한 인덱스들
CREATE INDEX idx_users_email ON users(email);                                    -- 로그인 성능
CREATE INDEX idx_insurance_companies_code ON insurance_companies(code);          -- 보험사 검색
CREATE INDEX idx_insurance_products_company_id ON insurance_products(company_id); -- 상품 검색
CREATE INDEX idx_insurance_clauses_product_id ON insurance_clauses(product_id);   -- 조항 검색

-- 환자 정보 검색 최적화
CREATE INDEX idx_medical_diagnoses_patient_ssn ON medical_diagnoses(patient_ssn);
CREATE INDEX idx_claims_patient_ssn ON claims(patient_ssn);
CREATE INDEX idx_user_contracts_patient_ssn ON user_contracts(patient_ssn);
CREATE INDEX idx_user_subscriptions_patient_ssn ON user_subscriptions(patient_ssn);

-- 업무 처리 최적화
CREATE INDEX idx_medical_diagnoses_user_id ON medical_diagnoses(user_id);
CREATE INDEX idx_medical_receipts_user_id ON medical_receipts(user_id);
CREATE INDEX idx_claims_user_id ON claims(user_id);
CREATE INDEX idx_claims_diagnosis_id ON claims(diagnosis_id);
CREATE INDEX idx_claims_receipt_id ON claims(receipt_id);
```

## 📋 ERD Cloud 사용법

1. **ERD Cloud** 접속: https://www.erdcloud.com/
2. **새 프로젝트** 생성
3. **Import SQL** 선택
4. 위의 스키마 코드를 복사해서 붙여넣기

## 🎯 **핵심 관계 요약**

### 📊 **테이블 간 의존성 순서**
```
1. users (보험사 직원) - 기본 테이블
2. insurance_companies (보험사) - 기본 테이블
3. insurance_products (보험상품) - companies 참조
4. insurance_clauses (보험조항) - products 참조
5. user_contracts (환자계약) - users, products 참조
6. user_subscriptions (특약가입) - users, contracts, clauses 참조
7. medical_diagnoses (진단서) - users 참조
8. medical_receipts (영수증) - users 참조
9. claims (보험금청구) - users, diagnoses, receipts 참조
10. claim_calculations (계산상세) - claims, clauses 참조
11. forgery_analysis (위조분석) - diagnoses, receipts 참조
```

### 🔑 **중요한 비즈니스 규칙**
- **환자 식별**: 주민번호(`patient_ssn`)로 환자 구분
- **문서 연결**: 진단서 + 영수증 = 1개 청구
- **보험금 계산**: 청구 → 특약 매칭 → 자동 계산
- **위조 검증**: 진단서 + 영수증 동시 분석
5. **Generate** 클릭하면 자동으로 ERD 생성!

## 🎯 시각화 권장 사항

1. **색상 구분**
   - 🟦 **파랑**: 보험사/상품/조항 (비즈니스 구조)
   - 🟩 **초록**: 사용자/계약 (고객 관리)
   - 🟨 **노랑**: 의료정보 (진단서/영수증)
   - 🟥 **빨강**: 청구/계산 (핵심 비즈니스)
   - 🟪 **보라**: 분석 시스템 (부가 기능)

2. **레이아웃 배치**
   - 왼쪽: 보험사 구조
   - 중앙: 환자/의료 정보
   - 오른쪽: 청구/계산 프로세스

## 💰 **금액 관련 상세 설명**

### 📊 **금액 필드별 의미**

#### 1. **medical_receipts.total_amount**
- **의미**: 영수증에 명시된 **실제 치료비 총액**
- **예시**: 1,500,000원 (병원에서 실제 청구한 금액)
- **용도**: 보험금 계산의 기준이 되는 실제 치료비

#### 2. **claims.claim_amount**
- **의미**: 영수증의 총금액을 기반으로 **청구하는 보험금**
- **예시**: 1,500,000원 (영수증의 total_amount와 동일)
- **용도**: 청구자가 요청하는 보험금 (실제 치료비 기준)

#### 3. **claim_calculations.calculated_amount**
- **의미**: 특약별로 **실제 지급될 보험금**
- **예시**: 
  - 실손의료비: 1,200,000원 (80% 적용)
  - 수술비: 500,000원 (정액)
  - 입원비: 150,000원 (3일 × 50,000원)
- **용도**: 각 특약별 실제 지급 보험금

### 🔄 **보험금 계산 흐름**

```
1. 영수증 등록
   ↓
2. medical_receipts.total_amount = 1,500,000원 (실제 치료비)
   ↓
3. 청구 생성
   ↓
4. claims.claim_amount = 1,500,000원 (영수증 총금액 기준)
   ↓
5. 특약별 계산
   ↓
6. claim_calculations.calculated_amount
   ├── 실손의료비: 1,200,000원 (80% 적용)
   ├── 수술비: 500,000원 (정액)
   └── 입원비: 150,000원 (일당)
   ↓
7. 최종 지급 보험금 = 1,850,000원 (특약별 계산 합계)
```

### 📋 **실제 데이터 예시**

#### **환자 정보**
- **이름**: 김철수
- **진단**: 급성 맹장염
- **입원일수**: 3일
- **실제 치료비**: 1,500,000원

#### **가입 보험**
- **상품**: 실손의료비보장보험
- **특약1**: 실손의료비담보 (80% 적용, 최대 1,000만원)
- **특약2**: 수술비담보 (정액 50만원)
- **특약3**: 입원비담보 (일당 5만원, 최대 30일)

#### **보험금 계산**
```
1. medical_receipts.total_amount = 1,500,000원
2. claims.claim_amount = 1,500,000원
3. claim_calculations:
   ├── 실손의료비: 1,500,000 × 80% = 1,200,000원
   ├── 수술비: 500,000원 (정액)
   └── 입원비: 3일 × 50,000원 = 150,000원
4. 총 지급 보험금: 1,850,000원
```

### ⚠️ **주의사항**

1. **claim_amount vs calculated_amount**
   - `claim_amount`: 청구자가 요청하는 금액 (영수증 기준)
   - `calculated_amount`: 실제 지급될 금액 (특약별 계산)

2. **한도 체크**
   - 각 특약별 `max_total` 한도 확인
   - 총 보험금이 한도를 초과하지 않도록 계산

3. **중복 지급 방지**
   - 같은 치료에 대해 여러 특약이 중복 적용되지 않도록 로직 필요
   - 예: 실손의료비 + 수술비 + 입원비는 각각 다른 항목

4. **실제 지급 금액**
   - 최종 지급 금액은 `claim_calculations`의 합계
   - `claims.claim_amount`는 청구 기준일 뿐, 실제 지급 금액과 다를 수 있음 