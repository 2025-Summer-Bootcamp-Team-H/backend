# 보험 청구 백엔드 시스템

## 주요 기능
- 현실적인 더미데이터 자동 생성 (환자, 진단서, 영수증, 청구, 보험가입 등)
- 청구 목록/검색/상세/통계/삭제 API 제공
- 동명이인, 상태별 검색, 통계/차트/트렌드 분석 지원
- 실전 서비스 플로우와 100% 호환 (OCR→DB→Claim→통계)
- CI/CD, 테스트, 린트, 배포 자동화

## 실행 방법
```bash
# 도커 환경에서 실행
cd backend
# 빌드 및 실행
docker-compose up -d --build
# 더미데이터 생성
docker exec -it insurance_backend python utils/scripts/create_final_dummy_data.py
```

## 주요 API 엔드포인트
- `GET /api/v1/claims` : 전체 청구 목록 조회
- `GET /api/v1/claims/search?patient_name=XXX&status=YYY` : 이름/상태별 청구 검색 (응답 포맷 동일)
- `GET /api/v1/claims/{claim_id}` : 청구 상세정보
- `GET /api/v1/claims/statistics/{claim_id}` : 청구 상세 통계/차트 데이터
- `DELETE /api/v1/claims/{claim_id}` : 개별 청구 삭제
- `DELETE /api/v1/claims` : 전체 청구 삭제

## 개발/배포/테스트 플로우
- 더미데이터/테스트/실전 데이터 모두 동일한 플로우로 동작
- 프론트엔드와 API 응답 포맷 일관성 보장
- CI: PR/커밋 시 자동 테스트/빌드/린트 실행

## 팀 협업 가이드
- PR 작성 시: 변경 요약, 테스트 방법, 리뷰 요청 명확히
- 더미데이터/통계/검색/삭제/상세 등 주요 기능 위주로 리뷰
- OCR/이미지→DB 파트는 별도 팀원 담당, 백엔드는 API/DB/통계/삭제 등 담당

---
자세한 내용은 TEAM_GUIDE.md, 가이드.md 참고 