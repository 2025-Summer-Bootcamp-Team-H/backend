# 🚀 배포 준비 체크리스트

## 📋 사전 준비사항

### ✅ 환경변수 파일 설정
- [ ] `env.example` → `.env` 복사 (로컬 개발용)
- [ ] `env.example` → `env.prod` 복사 (프로덕션용)
- [ ] 실제 API 키들로 수정
- [ ] JWT 시크릿 키 설정
- [ ] 데이터베이스 비밀번호 설정

### ✅ Docker 환경 확인
- [ ] Docker 설치 확인
- [ ] Docker Compose 설치 확인
- [ ] 포트 충돌 확인 (5432, 8000, 8080, 80, 443)

### ✅ 파일 권한 확인
- [ ] `uploads/` 디렉토리 생성
- [ ] 파일 쓰기 권한 확인
- [ ] 로그 디렉토리 생성

## 🐳 로컬 테스트

### ✅ Docker Compose 테스트
```bash
# 1. 환경변수 설정
cp env.example .env
# .env 파일에서 실제 값들로 수정

# 2. 컨테이너 빌드 및 실행
docker-compose up --build -d

# 3. 서비스 상태 확인
docker-compose ps

# 4. 로그 확인
docker-compose logs backend
docker-compose logs postgres
```

### ✅ API 테스트
```bash
# 1. 헬스체크
curl http://localhost:8000/health

# 2. 설정 확인
curl http://localhost:8000/config

# 3. API 문서 확인
curl http://localhost:8000/docs
```

### ✅ 데이터베이스 테스트
```bash
# 1. pgAdmin 접속
# http://localhost:8080
# admin@insurance.com / admin123

# 2. 데이터베이스 연결 확인
# Host: postgres
# Port: 5432
# Database: insurance_system
# Username: postgres
# Password: postgres123
```

## 🌐 프로덕션 배포

### ✅ GCP 서버 준비
```bash
# 1. 서버에 프로젝트 클론
git clone <your-repo>
cd backend

# 2. 프로덕션 환경변수 설정
cp env.example env.prod
# env.prod 파일에서 실제 값들로 수정

# 3. 프로덕션 모드로 실행
docker-compose -f docker-compose.prod.yml up -d
```

### ✅ AWS 배포
```bash
# 1. AWS CLI 설정
aws configure

# 2. 배포 스크립트 실행
./deploy/aws-deploy.sh ap-northeast-2 insurance-cluster
```

### ✅ GCP Cloud Run 배포
```bash
# 1. GCP CLI 설정
gcloud auth login
gcloud config set project <your-project-id>

# 2. 배포 스크립트 실행
./deploy/gcp-deploy.sh <project-id> asia-northeast3
```

## 🔧 배포 후 확인사항

### ✅ 서비스 상태 확인
- [ ] 모든 컨테이너 실행 중
- [ ] 데이터베이스 연결 성공
- [ ] API 응답 정상
- [ ] 로그 에러 없음

### ✅ 보안 확인
- [ ] 프로덕션에서 포트 노출 제한
- [ ] 환경변수 안전하게 관리
- [ ] SSL 인증서 설정 (선택사항)

### ✅ 성능 확인
- [ ] 응답 시간 측정
- [ ] 메모리 사용량 확인
- [ ] CPU 사용량 확인

## 📊 모니터링 설정

### ✅ 로그 모니터링
- [ ] Docker 로그 설정
- [ ] 애플리케이션 로그 설정
- [ ] 에러 알림 설정

### ✅ 메트릭 수집
- [ ] CPU/메모리 사용량
- [ ] API 응답 시간
- [ ] 데이터베이스 성능

## 🚨 문제 해결

### ✅ 일반적인 문제들
- [ ] 포트 충돌 해결
- [ ] 환경변수 오류 해결
- [ ] 데이터베이스 연결 오류 해결
- [ ] 한글 파일명 인코딩 문제 해결

### ✅ 로그 확인 명령어
```bash
# 컨테이너 로그 확인
docker-compose logs -f backend
docker-compose logs -f postgres

# 특정 서비스 로그 확인
docker-compose logs -f --tail=100 backend

# 에러 로그만 확인
docker-compose logs backend | grep ERROR
``` 