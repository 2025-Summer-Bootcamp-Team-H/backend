# 팀 개발/협업 가이드

## 주요 개발/협업 규칙
- PR 작성 시 변경 요약, 테스트 방법, 리뷰 요청 명확히
- 더미데이터/통계/검색/삭제/상세 등 주요 기능 위주로 리뷰
- API 응답 포맷 일관성 유지, 프론트와 협업 시 샘플 데이터/응답 공유
- OCR/이미지→DB 파트는 별도 팀원 담당, 백엔드는 API/DB/통계/삭제 등 담당

## 개발/배포/테스트 플로우
1. 도커 환경에서 개발/테스트/배포
2. 더미데이터 생성: `docker exec -it insurance_backend python utils/scripts/create_final_dummy_data.py`
3. 주요 API 테스트: Swagger UI(/docs) 또는 curl/Postman 등 활용
4. PR/커밋 시 자동 테스트/빌드/린트(CI) 실행

## 역할 분담
- OCR/이미지→DB: 팀원 A, B
- 백엔드 API/DB/통계/삭제/검색: 본인(백엔드 리드)
- 프론트엔드: 팀원 C, D

## 실전 서비스 플로우
1. 이미지 업로드 → OCR 추출
2. DB(MedicalDiagnosis, MedicalReceipt 등)에 insert
3. Claim 생성(진단서/영수증 PK로)
4. 통계/차트/검색/상세/삭제 등 API 활용

---
자세한 내용은 README.md, 가이드.md 참고 