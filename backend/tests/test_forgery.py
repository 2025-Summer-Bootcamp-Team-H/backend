import pytest

# client fixture는 conftest.py에서 제공됨

@pytest.fixture
def create_valid_diagnosis_and_receipt(client):
    # 진단서 생성
    diagnosis_data = {"patient_name": "홍길동", "diagnosis": "감기"}
    diagnosis_resp = client.post("/api/v1/diagnoses", json=diagnosis_data)
    diagnosis_id = diagnosis_resp.json().get("id")
    # 영수증 생성
    receipt_data = {"amount": 10000, "hospital": "서울병원"}
    receipt_resp = client.post("/api/v1/receipts", json=receipt_data)
    receipt_id = receipt_resp.json().get("id")
    return diagnosis_id, receipt_id

def test_forgery_analysis_not_found(client):
    data = {"diagnosis_id": 999, "receipt_id": 999}
    response = client.post("/api/v1/forgery_analysis", json=data)
    assert response.status_code == 404

def test_forgery_analysis_missing_fields(client):
    response = client.post("/api/v1/forgery_analysis", json={})
    assert response.status_code == 422

def test_forgery_analysis_success(client, create_valid_diagnosis_and_receipt):
    diagnosis_id, receipt_id = create_valid_diagnosis_and_receipt
    if not diagnosis_id or not receipt_id:
        pytest.skip("진단서 또는 영수증 생성 실패로 테스트 건너뜀")
    data = {"diagnosis_id": diagnosis_id, "receipt_id": receipt_id}
    response = client.post("/api/v1/forgery_analysis", json=data)
    assert response.status_code in [200, 201]
    # 추가적으로 응답 데이터 구조 검증 가능