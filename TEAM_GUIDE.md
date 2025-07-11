# 팀 가이드 - 보험금 청구 시스템

## 🎯 프로젝트 개요

AI 기반 보험금 청구 처리 시스템으로, 진단서와 영수증 이미지를 업로드하여 OCR 처리 후 AI를 통해 보험금을 자동으로 계산하고 위조분석을 수행합니다.

### 핵심 기능
- **이미지 업로드**: 진단서/영수증 이미지 업로드
- **OCR 처리**: AI를 통한 텍스트 추출 및 정보 인식
- **위조분석**: AI를 통한 문서 위조 여부 분석
- **보험금 계산**: 자동 보험금 계산 및 청구 생성
- **PDF 처리**: 보험 약관 PDF에서 조항 추출

## 🏗️ 시스템 아키텍처

### 기술 스택
- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL
- **Container**: Docker & Docker Compose
- **Reverse Proxy**: Nginx
- **AI/ML**: OpenAI GPT-4, Anthropic Claude
- **OCR**: Tesseract (한글 지원)
- **PDF**: PyMuPDF, pdfplumber

### 시스템 구조
```
사용자(보험사 직원) → FastAPI → PostgreSQL
                    ↓
                AI/OCR 처리
                    ↓
                보험금 계산
```

## 🚀 개발 환경 세팅

### 1. 필수 요구사항
- Docker Desktop
- Docker Compose
- Git
- VS Code (권장)

### 2. 프로젝트 클론
```bash
git clone [repository-url]
cd backend_1
```

### 3. 환경변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
POSTGRES_DB=insurance_db
POSTGRES_USER=insurance_user
POSTGRES_PASSWORD=your_secure_password
JWT_SECRET_KEY=your_jwt_secret_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 4. 컨테이너 실행
```bash
# 개발 환경 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f backend
```

### 5. 접속 확인
- **Swagger UI**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:8080 (admin@insurance.com / admin123)

## 📁 프로젝트 구조 상세

### backend/ 폴더
```
backend/
├── api/                    # API 엔드포인트
│   ├── auth.py            # 인증 (회원가입, 로그인)
│   ├── upload.py          # 이미지 업로드
│   ├── ocr.py             # OCR 처리
│   ├── medical.py         # 진단서/영수증 정보
│   ├── forgeries.py       # 위조분석
│   ├── claims.py          # 보험금 청구
│   ├── admin.py           # 관리자 기능
│   └── pdf.py             # PDF 처리
├── models/                 # 데이터베이스 모델
│   ├── models.py          # SQLAlchemy 모델
│   ├── database.py        # DB 연결
│   └── schemas.py         # Pydantic 스키마
├── services/              # 비즈니스 로직
│   ├── claim_calculator.py # 보험금 계산
│   ├── pdf_processor.py   # PDF 처리
│   └── ai_config.py       # AI 설정
├── utils/                 # 유틸리티
│   ├── scripts/           # 스크립트
│   └── sql/               # SQL 파일
└── main.py               # FastAPI 앱
```

### 주요 파일 설명

#### API 파일들
- **auth.py**: JWT 기반 인증, 회원가입/로그인
- **upload.py**: 진단서/영수증 이미지 업로드
- **ocr.py**: AI 기반 OCR 처리 및 정보 수정
- **medical.py**: 진단서/영수증 정보 조회/수정
- **forgeries.py**: AI 기반 위조분석
- **claims.py**: 보험금 청구 생성
- **admin.py**: 관리자용 청구 조회/통계
- **pdf.py**: PDF 보험조항 추출

#### 모델 파일들
- **models.py**: 모든 DB 테이블 정의
- **database.py**: PostgreSQL 연결 설정
- **schemas.py**: API 요청/응답 스키마

#### 서비스 파일들
- **claim_calculator.py**: 보험금 계산 로직
- **pdf_processor.py**: PDF 처리 및 조항 추출
- **ai_config.py**: OpenAI/Anthropic 설정

## 🗄️ 데이터베이스 구조

### 주요 테이블

#### 1. users (보험사 직원)
```sql
- id: 직원 ID
- email: 이메일 (로그인용)
- name: 이름
- password: 해시된 비밀번호
- is_deleted: 소프트 삭제 플래그
```

#### 2. medical_diagnoses (진단서)
```sql
- id: 진단서 ID
- user_id: 처리한 직원 ID
- patient_name: 피보험자 이름
- patient_ssn: 피보험자 주민번호
- diagnosis_name: 진단명
- hospital_name: 병원명
- admission_days: 입원일수
- image_url: 이미지 파일 경로
```

#### 3. medical_receipts (영수증)
```sql
- id: 영수증 ID
- user_id: 처리한 직원 ID
- patient_name: 피보험자 이름
- total_amount: 총 의료비
- hospital_name: 병원명
- image_url: 이미지 파일 경로
```

#### 4. claims (보험금 청구)
```sql
- id: 청구 ID
- user_id: 처리한 직원 ID
- patient_name: 피보험자 이름
- diagnosis_id: 진단서 ID
- receipt_id: 영수증 ID
- claim_amount: 청구 금액 (영수증의 총금액을 기반으로 계산)
- status: 청구 상태 (pending/approved/rejected)
```

#### 5. claim_calculations (보험금 계산)
```sql
- id: 계산 ID
- claim_id: 청구 ID
- clause_id: 특약 ID
- calculated_amount: 계산된 보험금
- calculation_logic: 계산 로직
```

## 🔧 개발 가이드

### 1. 로컬 개발 환경

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r backend/requirements.txt

# 환경변수 설정
export DATABASE_URL="postgresql://user:pass@localhost:5432/db"
export OPENAI_API_KEY="your_key"
export ANTHROPIC_API_KEY="your_key"

# 로컬 실행
cd backend
uvicorn main:app --reload
```

### 2. 컨테이너 관리

```bash
# 컨테이너 시작
docker-compose up -d

# 컨테이너 중지
docker-compose down

# 특정 서비스만 재시작
docker-compose restart backend

# 로그 확인
docker-compose logs -f backend
docker-compose logs -f postgres

# 컨테이너 재빌드
docker-compose build --no-cache backend
```

### 3. 데이터베이스 관리

```bash
# DB 마이그레이션
docker-compose exec backend alembic upgrade head

# 더미 데이터 생성
docker-compose exec backend python utils/scripts/create_final_dummy_data.py

# DB 접속
docker-compose exec postgres psql -U insurance_user -d insurance_db
```

### 4. 테스트

```bash
# 전체 테스트 실행
docker-compose exec backend pytest

# 특정 테스트 실행
docker-compose exec backend pytest tests/test_auth.py -v

# 커버리지 확인
docker-compose exec backend pytest --cov=backend
```

## 📚 API 사용 가이드

### 1. 인증 플로우

```bash
# 1. 회원가입
curl -X POST "http://localhost:8000/api/v1/users/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"홍길동","password":"password123"}'

# 2. 로그인
curl -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 3. 토큰 사용
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 이미지 업로드

```bash
# 진단서 업로드
curl -X POST "http://localhost:8000/api/v1/diagnoses/images" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@diagnosis.jpg"

# 영수증 업로드
curl -X POST "http://localhost:8000/api/v1/receipts/images" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@receipt.jpg"
```

### 3. OCR 처리

```bash
# 진단서 OCR
curl -X PATCH "http://localhost:8000/api/v1/diagnoses/ocr/1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 영수증 OCR
curl -X PATCH "http://localhost:8000/api/v1/receipts/ocr/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 보험금 청구

```bash
# 청구 생성
curl -X POST "http://localhost:8000/api/v1/claim/1/1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 청구 조회
curl -X GET "http://localhost:8000/api/v1/claims/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔍 디버깅 가이드

### 1. 로그 확인

```bash
# 백엔드 로그
docker-compose logs -f backend

# 데이터베이스 로그
docker-compose logs -f postgres

# Nginx 로그
docker-compose logs -f nginx
```

### 2. 일반적인 문제 해결

#### 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -ano | findstr :8000

# docker-compose.yml에서 포트 변경
ports:
  - "8001:8000"
```

#### 데이터베이스 연결 실패
```bash
# DB 컨테이너 상태 확인
docker-compose ps postgres

# DB 재시작
docker-compose restart postgres
```

#### AI API 키 오류
```bash
# 환경변수 확인
docker-compose exec backend env | grep API_KEY

# .env 파일 확인
cat .env
```

### 3. 개발 도구

#### Swagger UI
- URL: http://localhost:8000/docs
- API 테스트 및 문서 확인

#### pgAdmin
- URL: http://localhost:8080
- 계정: admin@insurance.com / admin123
- 데이터베이스 관리

## 🚀 배포 가이드

### 1. 개발 환경
```bash
docker-compose up -d
```

### 2. 운영 환경
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 3. 환경변수 설정 (운영)
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/db
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
JWT_SECRET_KEY=your_secret
```

## 📋 작업 체크리스트

### 신규 팀원 온보딩
- [ ] 프로젝트 클론
- [ ] Docker 설치 확인
- [ ] 환경변수 설정
- [ ] 컨테이너 실행
- [ ] Swagger UI 접속 확인
- [ ] API 테스트
- [ ] DB 마이그레이션
- [ ] 더미 데이터 생성

### 개발 시작 전
- [ ] 브랜치 생성
- [ ] 로컬 환경 확인
- [ ] 테스트 실행
- [ ] 코드 리뷰 준비

### 배포 전
- [ ] 테스트 통과 확인
- [ ] 환경변수 설정
- [ ] 데이터베이스 백업
- [ ] SSL 인증서 설정

## 📞 문의 및 지원

### 팀 내 문의
- 기술적 이슈: GitHub Issues
- 긴급 문의: 팀 채널

### 외부 리소스
- FastAPI 문서: https://fastapi.tiangolo.com/
- PostgreSQL 문서: https://www.postgresql.org/docs/
- Docker 문서: https://docs.docker.com/

## 📝 코딩 컨벤션

### Python
- PEP 8 스타일 가이드 준수
- 함수/변수명: snake_case
- 클래스명: PascalCase
- 상수: UPPER_CASE

### API
- 엔드포인트: kebab-case
- HTTP 메서드: GET, POST, PUT, PATCH, DELETE
- 상태 코드: 200, 201, 400, 401, 404, 500

### 데이터베이스
- 테이블명: snake_case
- 컬럼명: snake_case
- 인덱스: idx_table_column

---

**마지막 업데이트**: 2024년 7월 11일 