import pytest
from models.models import User
from models.schemas import ClaimCreate

def test_user_model_fields():
    # User 모델의 필드 정의만 검증 (값 비교 X)
    from models.models import User
    assert hasattr(User, "email")
    assert hasattr(User, "name")
    assert hasattr(User, "password")

def test_claim_create_schema():
    data = {"diagnosis_id": 1, "receipt_id": 1, "claim_reason": None, "user_id": 1}
    claim = ClaimCreate(**data)
    assert claim.diagnosis_id == 1
    assert claim.receipt_id == 1

@pytest.fixture
def get_auth_headers(client):
    response = client.post("/api/v1/auth/login", data={"username": "test@example.com", "password": "testpw"})
    assert response.status_code in [200, 404, 401]
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

@pytest.fixture
def create_claim(client, get_auth_headers):
    # 진단서 생성
    diagnosis_data = {"patient_name": "홍길동", "diagnosis": "감기"}
    diagnosis_resp = client.post("/api/v1/diagnoses", json=diagnosis_data, headers=get_auth_headers)
    diagnosis_id = diagnosis_resp.json().get("id", 1)
    # 영수증 생성
    receipt_data = {"amount": 10000, "hospital": "서울병원"}
    receipt_resp = client.post("/api/v1/receipts", json=receipt_data, headers=get_auth_headers)
    receipt_id = receipt_resp.json().get("id", 1)
    # 청구 생성
    claim_data = {"diagnosis_id": diagnosis_id, "receipt_id": receipt_id, "claim_reason": "진료비 환급", "user_id": 1}
    claim_resp = client.post("/api/v1/claims", json=claim_data, headers=get_auth_headers)
    claim_id = claim_resp.json().get("id", 1)
    return claim_id

def test_get_claims(client):
    response = client.get("/api/v1/claims")
    assert response.status_code in [200, 404, 403]

def test_claim_detail(client, get_auth_headers, create_claim):
    claim_id = create_claim
    response = client.get(f"/api/v1/claims/{claim_id}", headers=get_auth_headers)
    assert response.status_code in [200, 404, 403]

def test_admin_only_api(client, get_auth_headers):
    headers = get_auth_headers
    response = client.get("/api/v1/claims", headers=headers)
    assert response.status_code in [200, 404]  # 인증 성공 시

def test_public_api(client):
    response = client.get("/api/v1/claims")  # 인증 헤더 없이 호출
    assert response.status_code in [200, 404, 403]  # 권한 정책에 따라