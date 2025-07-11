#!/bin/bash

# AWS 배포 스크립트 (ECS Fargate + RDS)
# 사용법: ./deploy/aws-deploy.sh [region] [cluster-name]

set -e

# 기본 설정
REGION=${1:-"ap-northeast-2"}  # 서울 리전
CLUSTER_NAME=${2:-"insurance-cluster"}
SERVICE_NAME="insurance-backend"
TASK_FAMILY="insurance-task"
IMAGE_NAME="insurance-backend:latest"

echo "🚀 AWS 배포 시작"
echo "리전: ${REGION}"
echo "클러스터: ${CLUSTER_NAME}"
echo "서비스명: ${SERVICE_NAME}"

# 1. AWS CLI 설치 확인
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI가 설치되지 않았습니다."
    echo "설치 방법: https://aws.amazon.com/cli/"
    exit 1
fi

# 2. ECR 리포지토리 생성
echo "📦 ECR 리포지토리 생성 중..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${SERVICE_NAME}"

aws ecr describe-repositories --repository-names ${SERVICE_NAME} --region ${REGION} || \
aws ecr create-repository --repository-name ${SERVICE_NAME} --region ${REGION}

# 3. Docker 이미지 빌드 및 푸시
echo "🐳 Docker 이미지 빌드 및 푸시 중..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_URI}

docker build -f backend/Dockerfile.prod -t ${SERVICE_NAME} ./backend
docker tag ${SERVICE_NAME}:latest ${ECR_URI}:latest
docker push ${ECR_URI}:latest

# 4. VPC 및 보안 그룹 설정
echo "🌐 VPC 설정 중..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text --region ${REGION})
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --query "Subnets[*].SubnetId" --output text --region ${REGION})

# 보안 그룹 생성
SG_ID=$(aws ec2 create-security-group \
    --group-name insurance-sg \
    --description "Insurance API Security Group" \
    --vpc-id ${VPC_ID} \
    --region ${REGION} \
    --query 'GroupId' --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=insurance-sg" \
    --query "SecurityGroups[0].GroupId" --output text --region ${REGION})

# 보안 그룹 규칙 추가
aws ec2 authorize-security-group-ingress \
    --group-id ${SG_ID} \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region ${REGION} 2>/dev/null || true

# 5. RDS 인스턴스 생성 (PostgreSQL)
echo "🗄️ RDS 인스턴스 생성 중..."
DB_INSTANCE_ID="insurance-postgres"
DB_NAME="insurance_system"
DB_USER="postgres"
DB_PASSWORD=$(openssl rand -base64 32)

# RDS 서브넷 그룹 생성
aws rds create-db-subnet-group \
    --db-subnet-group-name insurance-subnet-group \
    --db-subnet-group-description "Insurance DB Subnet Group" \
    --subnet-ids ${SUBNET_IDS} \
    --region ${REGION} 2>/dev/null || true

# RDS 인스턴스 생성
aws rds create-db-instance \
    --db-instance-identifier ${DB_INSTANCE_ID} \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username ${DB_USER} \
    --master-user-password ${DB_PASSWORD} \
    --allocated-storage 20 \
    --db-name ${DB_NAME} \
    --db-subnet-group-name insurance-subnet-group \
    --vpc-security-group-ids ${SG_ID} \
    --backup-retention-period 7 \
    --storage-encrypted \
    --region ${REGION} 2>/dev/null || true

echo "⏳ RDS 인스턴스 생성 대기 중..."
aws rds wait db-instance-available --db-instance-identifier ${DB_INSTANCE_ID} --region ${REGION}

# RDS 엔드포인트 가져오기
DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier ${DB_INSTANCE_ID} \
    --query "DBInstances[0].Endpoint.Address" \
    --output text --region ${REGION})

# 6. Systems Manager Parameter Store에 환경변수 저장
echo "🔐 Parameter Store에 환경변수 저장 중..."
aws ssm put-parameter \
    --name "/insurance/db-password" \
    --value "${DB_PASSWORD}" \
    --type "SecureString" \
    --region ${REGION} --overwrite

aws ssm put-parameter \
    --name "/insurance/openai-api-key" \
    --value "your-openai-api-key-here" \
    --type "SecureString" \
    --region ${REGION} --overwrite

aws ssm put-parameter \
    --name "/insurance/jwt-secret-key" \
    --value "$(openssl rand -base64 32)" \
    --type "SecureString" \
    --region ${REGION} --overwrite

# 7. ECS 클러스터 생성
echo "🏗️ ECS 클러스터 생성 중..."
aws ecs create-cluster \
    --cluster-name ${CLUSTER_NAME} \
    --capacity-providers FARGATE \
    --region ${REGION} 2>/dev/null || true

# 8. 태스크 정의 생성
echo "📋 ECS 태스크 정의 생성 중..."
cat > task-definition.json << EOF
{
    "family": "${TASK_FAMILY}",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "1024",
    "memory": "2048",
    "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "${SERVICE_NAME}",
            "image": "${ECR_URI}:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "DATABASE_URL",
                    "value": "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_ENDPOINT}:5432/${DB_NAME}"
                },
                {
                    "name": "ENVIRONMENT",
                    "value": "production"
                }
            ],
            "secrets": [
                {
                    "name": "OPENAI_API_KEY",
                    "valueFrom": "arn:aws:ssm:${REGION}:${ACCOUNT_ID}:parameter/insurance/openai-api-key"
                },
                {
                    "name": "JWT_SECRET_KEY",
                    "valueFrom": "arn:aws:ssm:${REGION}:${ACCOUNT_ID}:parameter/insurance/jwt-secret-key"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/${SERVICE_NAME}",
                    "awslogs-region": "${REGION}",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
EOF

aws ecs register-task-definition \
    --cli-input-json file://task-definition.json \
    --region ${REGION}

# 9. ECS 서비스 생성
echo "🚀 ECS 서비스 생성 중..."
aws ecs create-service \
    --cluster ${CLUSTER_NAME} \
    --service-name ${SERVICE_NAME} \
    --task-definition ${TASK_FAMILY} \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_IDS// /,}],securityGroups=[${SG_ID}],assignPublicIp=ENABLED}" \
    --region ${REGION} 2>/dev/null || true

# 10. Application Load Balancer 생성
echo "⚖️ Application Load Balancer 생성 중..."
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name insurance-alb \
    --subnets ${SUBNET_IDS} \
    --security-groups ${SG_ID} \
    --region ${REGION} \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || \
    aws elbv2 describe-load-balancers \
    --names insurance-alb \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text --region ${REGION})

# 11. 배포 완료 정보 출력
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns ${ALB_ARN} \
    --query 'LoadBalancers[0].DNSName' --output text --region ${REGION})

echo ""
echo "🎉 AWS 배포 완료!"
echo "로드밸런서 URL: http://${ALB_DNS}"
echo "API 문서: http://${ALB_DNS}/docs"
echo "헬스체크: http://${ALB_DNS}/health"
echo ""
echo "📋 중요 정보:"
echo "- RDS 엔드포인트: ${DB_ENDPOINT}"
echo "- 데이터베이스 비밀번호: ${DB_PASSWORD}"
echo "- OpenAI API 키는 Parameter Store에서 수정하세요"
echo ""
echo "🔧 다음 단계:"
echo "1. Parameter Store에서 OpenAI API 키 업데이트"
echo "2. 데이터베이스 스키마 초기화"
echo "3. 더미 데이터 생성"
echo "4. Route 53에서 도메인 설정"

# 임시 파일 정리
rm -f task-definition.json 