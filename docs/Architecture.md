# 진단서 자동 보상액 산정 서비스 아키텍처

## 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        프론트엔드 (React)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   사용자    │  │   진단서    │  │   보상액    │  │   관리  │ │
│  │   관리      │  │   업로드    │  │   조회      │  │   페이지│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP/HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (Nginx)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   인증      │  │   라우팅    │  │   로드      │  │   SSL   │ │
│  │   처리      │  │             │  │   밸런싱    │  │   종료  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP/HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    백엔드 서비스 (Node.js/Express)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   사용자    │  │   진단서    │  │   보상액    │  │   파일  │ │
│  │   서비스    │  │   처리      │  │   계산      │  │   관리  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI 처리 서비스 (Python)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   OCR       │  │   텍스트    │  │   정보      │  │   특약  │ │
│  │   엔진      │  │   추출      │  │   매칭      │  │   분석  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        데이터베이스 (MySQL)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   사용자    │  │   보험      │  │   진단서    │  │   보상  │ │
│  │   데이터    │  │   상품      │  │   데이터    │  │   계산  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      파일 스토리지 (AWS S3)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   원본      │  │   처리된    │  │   임시      │  │   백업  │ │
│  │   파일      │  │   파일      │  │   파일      │  │   파일  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 서비스별 상세 아키텍처

### 1. 프론트엔드 (React + TypeScript)
```
src/
├── components/          # 재사용 가능한 컴포넌트
│   ├── common/         # 공통 컴포넌트
│   ├── forms/          # 폼 컴포넌트
│   └── layout/         # 레이아웃 컴포넌트
├── pages/              # 페이지 컴포넌트
│   ├── auth/           # 인증 관련 페이지
│   ├── dashboard/      # 대시보드
│   ├── upload/         # 파일 업로드
│   └── results/        # 결과 조회
├── services/           # API 서비스
├── hooks/              # 커스텀 훅
├── utils/              # 유틸리티 함수
└── types/              # TypeScript 타입 정의
```

### 2. 백엔드 (Node.js + Express)
```
backend/
├── src/
│   ├── controllers/    # 컨트롤러
│   ├── services/       # 비즈니스 로직
│   ├── models/         # 데이터 모델
│   ├── middleware/     # 미들웨어
│   ├── routes/         # 라우트 정의
│   ├── utils/          # 유틸리티
│   └── config/         # 설정 파일
├── tests/              # 테스트 파일
└── docs/               # API 문서
```

### 3. AI 처리 서비스 (Python + FastAPI)
```
ai-service/
├── app/
│   ├── models/         # AI 모델
│   ├── processors/     # 데이터 처리기
│   ├── extractors/     # 정보 추출기
│   ├── matchers/       # 정보 매칭기
│   └── utils/          # 유틸리티
├── models/             # 학습된 모델 파일
├── data/               # 학습 데이터
└── tests/              # 테스트
```

## 데이터 플로우

### 1. 진단서 업로드 플로우
```
1. 사용자 → 프론트엔드: 진단서 파일 선택
2. 프론트엔드 → 백엔드: 파일 업로드 요청
3. 백엔드 → S3: 파일 저장
4. 백엔드 → AI 서비스: 파일 처리 요청
5. AI 서비스 → OCR: 텍스트 추출
6. AI 서비스 → 정보 추출: 진단 정보 파싱
7. AI 서비스 → 백엔드: 추출 결과 반환
8. 백엔드 → DB: 추출 정보 저장
9. 백엔드 → 프론트엔드: 처리 완료 응답
```

### 2. 보상액 계산 플로우
```
1. 사용자 → 프론트엔드: 보상액 계산 요청
2. 프론트엔드 → 백엔드: 계산 요청
3. 백엔드 → DB: 사용자 계약 정보 조회
4. 백엔드 → DB: 특약 정보 조회
5. 백엔드 → DB: 진단 정보 조회
6. 백엔드 → 계산 엔진: 보상액 계산
7. 백엔드 → DB: 계산 결과 저장
8. 백엔드 → 프론트엔드: 계산 결과 반환
```

## 기술 스택

### 프론트엔드
- **React 18** + TypeScript
- **Tailwind CSS** (스타일링)
- **React Query** (상태 관리)
- **React Hook Form** (폼 관리)
- **Axios** (HTTP 클라이언트)

### 백엔드
- **Node.js** + Express
- **TypeScript**
- **MySQL** (메인 데이터베이스)
- **Redis** (캐싱)
- **JWT** (인증)
- **Multer** (파일 업로드)

### AI 서비스
- **Python 3.9+**
- **FastAPI** (API 프레임워크)
- **OpenCV** (이미지 처리)
- **Tesseract** (OCR)
- **spaCy** (NLP)
- **scikit-learn** (머신러닝)

### 인프라
- **Docker** (컨테이너화)
- **Docker Compose** (로컬 개발)
- **AWS S3** (파일 스토리지)
- **Nginx** (리버스 프록시)
- **PM2** (프로세스 관리)

## 보안 고려사항

1. **파일 업로드 보안**
   - 파일 타입 검증
   - 파일 크기 제한
   - 바이러스 스캔

2. **데이터 보안**
   - 개인정보 암호화
   - HTTPS 통신
   - JWT 토큰 관리

3. **접근 제어**
   - 역할 기반 접근 제어 (RBAC)
   - API 요청 제한
   - 세션 관리

## 성능 최적화

1. **데이터베이스**
   - 인덱스 최적화
   - 쿼리 최적화
   - 연결 풀링

2. **캐싱**
   - Redis 캐싱
   - CDN 사용
   - 브라우저 캐싱

3. **비동기 처리**
   - 파일 처리 큐
   - 이메일 발송 큐
   - 로그 처리 