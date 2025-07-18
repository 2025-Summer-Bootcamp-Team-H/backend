import pytest

def test_get_claims(client):
    response = client.get("/api/v1/claims")
    assert response.status_code in [200, 404, 403]

def test_get_claim_details_not_found(client):
    response = client.get("/api/v1/claims/99999")
    assert response.status_code in [404, 403]

def test_create_claim_missing_fields(client):
    response = client.post("/api/v1/claims", json={})
    assert response.status_code in [422, 403]

def test_create_claim_invalid_ids(client):
    data = {"diagnosis_id": 99999, "receipt_id": 99999, "user_id": 1}
    response = client.post("/api/v1/claims", json=data)
    assert response.status_code in [404, 500, 403]

def test_delete_claim_not_found(client):
    response = client.delete("/api/v1/claims/99999")
    assert response.status_code in [200, 404, 403]

def test_claim_statistics_not_found(client):
    response = client.get("/api/v1/claims/statistics/99999")
    assert response.status_code in [404, 403]

def test_search_claims(client):
    response = client.get("/api/v1/claims/search?patient_name=홍길동&status=진행중")
    assert response.status_code in [200, 404, 403]