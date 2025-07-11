# 보험금 청구 시스템

AI 기반 보험금 청구 처리 시스템입니다. 진단서와 영수증 이미지를 업로드하여 OCR 처리 후, AI를 통해 보험금을 자동으로 계산하고 위조분석을 수행합니다.

## 🏗️ 프로젝트 구조

```
backend_1/
├── backend/                    # FastAPI 백엔드
│   ├── api/                   # API 엔드포인트
│   │   ├── auth.py           # 인증 관련 API
│   │   ├── upload.py         # 이미지 업로드 API
│   │   ├── ocr.py            # OCR 처리 API
│   │   ├── medical.py        # 진단서/영수증 정보 API
│   │   ├── forgeries.py      # 위조분석 API
│   │   ├── claims.py         # 보험금 청구 API
│   │   ├── admin.py          # 관리자 API
│   │   └── pdf.py            # PDF 처리 API
│   ├── models/               # 데이터베이스 모델
│   │   ├── models.py         # SQLAlchemy 모델
│   │   ├── database.py       # DB 연결 설정
│   │   └── schemas.py        # Pydantic 스키마
│   ├── services/             # 비즈니스 로직
│   │   ├── claim_calculator.py  # 보험금 계산
│   │   ├── pdf_processor.py     # PDF 처리
│   │   └── ai_config.py         # AI 설정
│   ├── utils/                # 유틸리티
│   │   ├── scripts/          # 스크립트
│   │   └── sql/              # SQL 파일
│   ├── input_pdfs/           # 입력 PDF 파일
│   ├── output_results/       # 출력 결과
│   ├── uploads/              # 업로드 파일
│   └── main.py               # FastAPI 앱
├── docs/                     # 문서
│   └── API_ENDPOINTS.md      # API 명세서
├── nginx/                    # Nginx 설정
├── docker-compose.yml        # 개발용 Docker Compose
├── docker-compose.prod.yml   # 운영용 Docker Compose
└── README.md                 # 프로젝트 가이드
```

## 🚀 빠른 시작

### 1. 환경 설정

#### 필수 요구사항
- Docker & Docker Compose
- Python 3.11 (로컬 개발시)

#### 환경변수 설정 (.env)
```bash
# 데이터베이스
POSTGRES_DB=insurance_db
POSTGRES_USER=insurance_user
POSTGRES_PASSWORD=your_password

# JWT 인증
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI API 키
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# pgAdmin
PGADMIN_PASSWORD=admin123
```

### 2. 개발 환경 실행

```bash
# 컨테이너 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f backend
```

### 3. 접속 정보

- **FastAPI Swagger UI**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:8080 (admin@insurance.com / admin123)
- **Nginx**: http://localhost:80

## 📚 API 문서

### 주요 API 엔드포인트

#### 인증
- `POST /users/signup` - 회원가입
- `POST /users/login` - 로그인
- `GET /users/me` - 내 정보 조회

#### 이미지 업로드
- `POST /diagnoses/images` - 진단서 업로드
- `POST /receipts/images` - 영수증 업로드

#### OCR 처리
- `PATCH /diagnoses/ocr/{diagnosis_id}` - 진단서 OCR
- `PATCH /receipts/ocr/{receipt_id}` - 영수증 OCR

#### 보험금 청구
- `POST /claim/{diagnosis_id}/{receipt_id}` - 청구 생성
- `GET /claims` - 청구 목록 조회
- `GET /claims/{claim_id}` - 청구 상세 조회

#### 위조분석
- `POST /diagnoses/forgeries/{diagnosis_id}` - 진단서 위조분석
- `POST /receipts/forgeries/{receipt_id}` - 영수증 위조분석

#### PDF 처리
- `POST /users/pdf/process` - PDF 보험조항 추출

**전체 API 명세**: [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md)

## 🗄️ 데이터베이스

### 주요 테이블

- **users**: 보험사 직원 정보
- **medical_diagnoses**: 진단서 정보
- **medical_receipts**: 영수증 정보
- **claims**: 보험금 청구 정보
- **claim_calculations**: 보험금 계산 결과
- **insurance_clauses**: 보험 조항 정보
- **user_contracts**: 계약 정보
- **user_subscriptions**: 가입 특약 정보
- **forgery_analysis**: 위조분석 결과

### DB 마이그레이션

```bash
# 마이그레이션 실행
docker-compose exec backend alembic upgrade head

# 더미 데이터 생성
docker-compose exec backend python utils/scripts/create_final_dummy_data.py
```

## 🔧 개발 가이드

### 로컬 개발 환경

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r backend/requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 수정

# 로컬 실행
cd backend
uvicorn main:app --reload
```

### 컨테이너 관리

```bash
# 컨테이너 시작
docker-compose up -d

# 컨테이너 중지
docker-compose down

# 로그 확인
docker-compose logs -f [service_name]

# 컨테이너 재빌드
docker-compose build --no-cache
```

### 테스트

```bash
# 테스트 실행
docker-compose exec backend pytest

# 특정 테스트 실행
docker-compose exec backend pytest tests/test_auth.py
```

## 🚀 운영 배포

### 프로덕션 환경

```bash
# 운영용 컨테이너 시작
docker-compose -f docker-compose.prod.yml up -d

# SSL 인증서 설정
# nginx/ssl/ 폴더에 인증서 파일 배치
```

### 환경변수 (운영)

```bash
# 운영용 환경변수
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/db
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
JWT_SECRET_KEY=your_secret
```

## 📁 주요 폴더 설명

### backend/
- **api/**: REST API 엔드포인트
- **models/**: 데이터베이스 모델 및 스키마
- **services/**: 비즈니스 로직 (보험금 계산, AI 처리 등)
- **utils/**: 유틸리티 스크립트 및 SQL 파일

### uploads/
- **diagnosis/**: 업로드된 진단서 이미지
- **receipts/**: 업로드된 영수증 이미지

### input_pdfs/
- 테스트용 보험 약관 PDF 파일들

### output_results/
- PDF 처리 결과 및 추출된 보험 조항

## 🔍 문제 해결

### 일반적인 문제

1. **포트 충돌**
   ```bash
   # 사용 중인 포트 확인
   netstat -ano | findstr :8000
   
   # docker-compose.yml에서 포트 변경
   ports:
     - "8001:8000"  # 8000 → 8001
   ```

2. **데이터베이스 연결 실패**
   ```bash
   # DB 컨테이너 상태 확인
   docker-compose ps postgres
   
   # DB 로그 확인
   docker-compose logs postgres
   ```

3. **AI API 키 오류**
   ```bash
   # 환경변수 확인
   docker-compose exec backend env | grep API_KEY
   ```

### 로그 확인

```bash
# 백엔드 로그
docker-compose logs -f backend

# 데이터베이스 로그
docker-compose logs -f postgres

# Nginx 로그
docker-compose logs -f nginx
```

## 🤝 기여 가이드

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해 주세요. 