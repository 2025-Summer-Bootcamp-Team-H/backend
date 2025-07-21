#!/bin/bash

# 🚀 빠른 배포 테스트 스크립트
# 사용법: ./deploy/quick-test.sh

set -e

echo "🚀 AI 보험금 청구 시스템 배포 테스트 시작"
echo "=========================================="

# 1. 환경변수 파일 확인
echo "📋 1. 환경변수 파일 확인 중..."
if [ ! -f ".env" ]; then
    echo "⚠️ .env 파일이 없습니다. env.example을 복사합니다."
    cp env.example .env
    echo "✅ .env 파일 생성됨"
    echo "💡 .env 파일에서 실제 API 키들을 설정하세요!"
else
    echo "✅ .env 파일 존재"
fi

# 2. Docker 환경 확인
echo "🐳 2. Docker 환경 확인 중..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose가 설치되지 않았습니다."
    exit 1
fi

echo "✅ Docker 환경 확인 완료"

# 3. 포트 충돌 확인
echo "🔍 3. 포트 충돌 확인 중..."
PORTS=(5432 8000 8080 80 443)
for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️ 포트 $port가 이미 사용 중입니다."
    else
        echo "✅ 포트 $port 사용 가능"
    fi
done

# 4. 디렉토리 생성
echo "📁 4. 필요한 디렉토리 생성 중..."
mkdir -p uploads/diagnosis
mkdir -p uploads/receipts
mkdir -p logs
echo "✅ 디렉토리 생성 완료"

# 5. Docker Compose 빌드 및 실행
echo "🐳 5. Docker Compose 빌드 및 실행 중..."
docker-compose down 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

# 6. 서비스 상태 확인
echo "📊 6. 서비스 상태 확인 중..."
sleep 10
docker-compose ps

# 7. API 테스트
echo "🔍 7. API 테스트 중..."
sleep 5

# 헬스체크
echo "📡 헬스체크 테스트..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health || echo "FAILED")
if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    echo "✅ 헬스체크 성공"
else
    echo "❌ 헬스체크 실패"
fi

# 설정 확인
echo "⚙️ 설정 확인 테스트..."
CONFIG_RESPONSE=$(curl -s http://localhost:8000/config || echo "FAILED")
if [[ $CONFIG_RESPONSE == *"environment"* ]]; then
    echo "✅ 설정 확인 성공"
else
    echo "❌ 설정 확인 실패"
fi

# 8. 데이터베이스 연결 확인
echo "🗄️ 8. 데이터베이스 연결 확인 중..."
DB_CONTAINER=$(docker-compose ps -q postgres)
if [ ! -z "$DB_CONTAINER" ]; then
    echo "✅ PostgreSQL 컨테이너 실행 중"
    
    # 데이터베이스 연결 테스트
    if docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        echo "✅ 데이터베이스 연결 성공"
    else
        echo "❌ 데이터베이스 연결 실패"
    fi
else
    echo "❌ PostgreSQL 컨테이너가 실행되지 않음"
fi

# 9. 로그 확인
echo "📋 9. 최근 로그 확인 중..."
echo "🔍 Backend 로그 (최근 10줄):"
docker-compose logs --tail=10 backend

echo "🔍 PostgreSQL 로그 (최근 5줄):"
docker-compose logs --tail=5 postgres

# 10. 완료 메시지
echo ""
echo "🎉 배포 테스트 완료!"
echo "=================="
echo "📊 서비스 상태:"
docker-compose ps

echo ""
echo "🌐 접속 정보:"
echo "- API 서버: http://localhost:8000"
echo "- API 문서: http://localhost:8000/docs"
echo "- pgAdmin: http://localhost:8080 (admin@insurance.com / admin123)"
echo "- Nginx: http://localhost:80"

echo ""
echo "🔧 유용한 명령어:"
echo "- 로그 확인: docker-compose logs -f backend"
echo "- 서비스 재시작: docker-compose restart"
echo "- 서비스 중지: docker-compose down"
echo "- 설정 확인: curl http://localhost:8000/config"

echo ""
echo "⚠️ 다음 단계:"
echo "1. .env 파일에서 실제 API 키들을 설정하세요"
echo "2. 더미 데이터 생성: curl -X POST http://localhost:8000/api/v1/dummy-data"
echo "3. API 테스트를 진행하세요" 