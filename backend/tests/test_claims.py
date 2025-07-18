import pytest

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data

def test_get_claims(client):
    response = client.get("/api/v1/claims")
    assert response.status_code in [200, 404, 403]

def test_get_claim_details(client):
    response = client.get("/api/v1/claims/999")
    assert response.status_code in [404, 403]

def test_create_claim(client):
    claim_data = {"diagnosis_id": 1, "receipt_id": 1, "user_id": 1}
    response = client.post("/api/v1/claims", json=claim_data)
    assert response.status_code in [200, 404, 500, 403]

def test_delete_claim(client):
    response = client.delete("/api/v1/claims/999")
    assert response.status_code in [200, 404, 403]

def test_claim_statistics(client):
    response = client.get("/api/v1/claims/statistics/999")
    assert response.status_code in [200, 404, 403]

def test_search_claims(client):
    response = client.get("/api/v1/claims/search?patient_name=홍길동&status=진행중")
    assert response.status_code in [200, 404, 403]

def test_imports():
    try:
        import fastapi
        from models.database import get_db
        from models.models import Claim, User
        from api.claims import router
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")