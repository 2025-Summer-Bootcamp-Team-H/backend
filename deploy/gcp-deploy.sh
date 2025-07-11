#!/bin/bash

# Google Cloud Platform 배포 스크립트
# 사용법: ./deploy/gcp-deploy.sh [project-id] [region]

set -e

# 기본 설정
PROJECT_ID=${1:-"insurance-claim-system"}
REGION=${2:-"asia-northeast3"}  # 서울 리전
SERVICE_NAME="insurance-backend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Google Cloud Platform 배포 시작"
echo "프로젝트 ID: ${PROJECT_ID}"
echo "리전: ${REGION}"
echo "서비스명: ${SERVICE_NAME}"

# 1. Google Cloud SDK 설치 확인
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK가 설치되지 않았습니다."
    echo "설치 방법: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# 2. 프로젝트 설정
echo "📝 프로젝트 설정 중..."
gcloud config set project ${PROJECT_ID}
gcloud config set run/region ${REGION}

# 3. 필요한 API 활성화
echo "🔧 필요한 API 활성화 중..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com

# 4. Cloud SQL 인스턴스 생성 (PostgreSQL)
echo "🗄️ Cloud SQL 인스턴스 생성 중..."
DB_INSTANCE_NAME="insurance-postgres"
DB_NAME="insurance_system"
DB_USER="postgres"
DB_PASSWORD=$(openssl rand -base64 32)

# Cloud SQL 인스턴스 존재 확인
if ! gcloud sql instances describe ${DB_INSTANCE_NAME} &> /dev/null; then
    gcloud sql instances create ${DB_INSTANCE_NAME} \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=${REGION} \
        --storage-type=SSD \
        --storage-size=10GB \
        --backup-start-time=02:00 \
        --enable-bin-log \
        --deletion-protection
    
    # 데이터베이스 생성
    gcloud sql databases create ${DB_NAME} --instance=${DB_INSTANCE_NAME}
    
    # 사용자 비밀번호 설정
    gcloud sql users set-password ${DB_USER} \
        --instance=${DB_INSTANCE_NAME} \
        --password=${DB_PASSWORD}
    
    echo "✅ Cloud SQL 인스턴스 생성 완료"
    echo "데이터베이스 비밀번호: ${DB_PASSWORD}"
else
    echo "ℹ️ Cloud SQL 인스턴스가 이미 존재합니다."
fi

# 5. Secret Manager에 환경변수 저장
echo "🔐 Secret Manager에 환경변수 저장 중..."
gcloud services enable secretmanager.googleapis.com

# 환경변수 시크릿 생성
echo -n "${DB_PASSWORD}" | gcloud secrets create db-password --data-file=-
echo -n "your-openai-api-key-here" | gcloud secrets create openai-api-key --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets create jwt-secret-key --data-file=-

# 6. Docker 이미지 빌드 및 푸시
echo "🐳 Docker 이미지 빌드 중..."
gcloud builds submit --tag ${IMAGE_NAME} ./backend

# 7. Cloud Run 서비스 배포
echo "☁️ Cloud Run 서비스 배포 중..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-env-vars="ENVIRONMENT=production" \
    --set-secrets="DATABASE_PASSWORD=db-password:latest" \
    --set-secrets="OPENAI_API_KEY=openai-api-key:latest" \
    --set-secrets="JWT_SECRET_KEY=jwt-secret-key:latest" \
    --set-env-vars="DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@/postgres?host=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME}" \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME} \
    --memory=2Gi \
    --cpu=2 \
    --max-instances=10 \
    --timeout=300

# 8. 배포 완료 정보 출력
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

echo ""
echo "🎉 배포 완료!"
echo "서비스 URL: ${SERVICE_URL}"
echo "API 문서: ${SERVICE_URL}/docs"
echo "헬스체크: ${SERVICE_URL}/health"
echo ""
echo "📋 중요 정보:"
echo "- 데이터베이스 비밀번호: ${DB_PASSWORD}"
echo "- OpenAI API 키는 Secret Manager에서 수정하세요"
echo "- SSL 인증서는 자동으로 제공됩니다"
echo ""
echo "🔧 다음 단계:"
echo "1. Secret Manager에서 OpenAI API 키 업데이트"
echo "2. 데이터베이스 스키마 초기화"
echo "3. 더미 데이터 생성" 