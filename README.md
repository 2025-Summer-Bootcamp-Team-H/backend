# AI 보험금 청구 시스템

AI 기반 보험금 청구 처리 시스템 - PDF에서 보험 조항을 추출하고 진단서를 분석하여 자동으로 보험금을 계산합니다.

---

## 🚀 빠른 시작

### 로컬 개발 환경
```bash
# 1. 환경변수 설정
cp env.example .env
# .env 파일에서 실제 API 키 등으로 수정

# 2. Docker Compose 실행
docker-compose up -d --build

# 3. 더미데이터 생성 (필요시)
docker exec -it insurance_backend python utils/scripts/create_final_dummy_data.py

# 4. API 테스트
curl http://localhost:8000/health
```

### 프로덕션 배포
```bash
# 1. 서버에서 프로덕션 환경변수 설정
cp env.example env.prod
# env.prod 파일에서 실제 값들로 수정 (API 키, DB 비번 등)

# 2. 프로덕션 모드로 실행
docker-compose -f docker-compose.prod.yml up -d --build
```

> ⚠️ **env.prod, .env.prod 등 실제 환경변수 파일은 git에 올리지 마세요!**
> (이미 .gitignore에 추가되어 있습니다)

---

## 📁 프로젝트 구조

```
backend/
├── .env                    # 로컬 개발용 환경변수 (git에 올리지 마세요)
├── env.prod                # 프로덕션용 환경변수 (git에 올리지 마세요)
├── env.example             # 환경변수 템플릿
├── docker-compose.yml      # 로컬 개발용 Docker 설정
├── docker-compose.prod.yml # 프로덕션용 Docker 설정
├── backend/                # 소스코드
│   ├── main.py             # FastAPI 앱
│   ├── api/                # API 라우터들
│   ├── models/             # 데이터베이스 모델
│   ├── services/           # 비즈니스 로직
│   ├── utils/              # 유틸리티/스크립트
│   └── ...
├── deploy/                 # 배포 스크립트
├── nginx/                  # Nginx 설정
└── uploads/                # 업로드 파일 저장소 (로컬 개발용)
```

---

## 🏗️ 개발/배포 워크플로우

### 로컬 개발
1. 코드 수정: `backend/` 폴더 내 파일 수정
2. 실시간 반영: 볼륨 마운트로 코드 변경 즉시 반영
3. 테스트: Swagger UI(/docs) 또는 curl/Postman 등 활용
4. 커밋: `git add . && git commit -m "메시지"`

### 프로덕션 배포
1. 코드 푸시: `git push origin main`
2. 서버에서 풀: `git pull origin main`
3. 프로덕션 실행: `docker-compose -f docker-compose.prod.yml up -d --build`

---

## 🌐 주요 접속 정보

### 로컬 개발 환경
- **API 서버**: http://localhost:8000
- **Swagger 문서**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:8080 (admin@insurance.com / admin123)
- **Nginx**: http://localhost:80

### 프로덕션 환경
- **API 서버**: https://your-domain.com
- **Swagger 문서**: https://your-domain.com/docs
- **Nginx**: https://your-domain.com (SSL)

---

## 🖼️ 이미지 반환 API
- 진단서 이미지: `GET /api/v1/images/diagnosis/{diagnosis_id}`
- 영수증 이미지: `GET /api/v1/images/receipt/{receipt_id}`
  - PK만 알면 프론트에서 `<img src="...">`로 바로 사용 가능
  - 클라우드 스토리지/로컬 모두 자동 지원

---

## 📚 주요 API 엔드포인트
- 보험금 청구 생성: `POST /api/v1/claims`
- 청구 목록 조회: `GET /api/v1/claims`
- 청구 상세 조회: `GET /api/v1/claims/{claim_id}`
- 진단서/영수증 업로드: `POST /api/v1/upload/diagnoses`, `POST /api/v1/upload/receipts`
- 진단서/영수증 정보 조회: `GET /api/v1/diagnoses/{diagnosis_id}`, `GET /api/v1/receipts/{receipt_id}`
- OCR 처리: `PATCH /api/v1/ocr/diagnoses/{diagnosis_id}`, `PATCH /api/v1/ocr/receipts/{receipt_id}`
- 위조분석: `POST /api/v1/forgery_analysis`

---

## 🛠️ 유용한 명령어

### 로컬 개발
```bash
# 서비스 시작
docker-compose up -d
# 서비스 중지
docker-compose down
# 로그 확인
docker-compose logs -f backend
# 설정 확인
curl http://localhost:8000/config
# 더미 데이터 생성
curl -X POST http://localhost:8000/api/v1/dummy-data
```

### 프로덕션
```bash
# 프로덕션 실행
docker-compose -f docker-compose.prod.yml up -d
# 프로덕션 중지
docker-compose -f docker-compose.prod.yml down
# 프로덕션 로그 확인
docker-compose -f docker-compose.prod.yml logs -f backend
```

---

## 🧩 환경변수 관리
- `.env` (로컬), `env.prod` (운영) 파일은 **절대 git에 올리지 마세요!**
- 템플릿(`env.example`)만 커밋
- 실제 값은 서버/로컬에만 보관

---

## 🚨 문제 해결

### 일반적인 문제들
1. **포트 충돌**: `lsof -i :8000`으로 확인
2. **환경변수 오류**: `.env`/`env.prod` 파일 확인
3. **DB 연결 오류**: PostgreSQL 컨테이너 상태 확인
4. **한글 파일명 문제**: 로케일/컨테이너 설정 확인
5. **경로 문제**: output_results, uploads 등 경로 자동 탐색 코드 적용

### 로그 확인
```bash
# Backend 로그
docker-compose logs -f backend
# PostgreSQL 로그
docker-compose logs -f postgres
# Nginx 로그
docker-compose logs -f nginx
```

---

## ✅ 배포 체크리스트
- [ ] 불필요한 파일/폴더 삭제 (api_backup, 테스트/더미/실험 코드 등)
- [ ] 민감정보 커밋 금지 (.env, env.prod 등)
- [ ] README/가이드 최신화
- [ ] .gitignore 재확인
- [ ] main.py, requirements.txt, docker-compose.yml 등 핵심 파일 최신화
- [ ] 서버/로컬 모두 정상 동작 확인

---

## 🤝 기여하기
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request 