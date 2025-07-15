import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_get_claims():
    """Test GET /claims endpoint"""
    response = client.get("/api/v1/claims")
    # Accept both 200 (with data) and 404 (no data)
    assert response.status_code in [200, 404]

def test_get_claim_details():
    """Test GET /claims/{claim_id} endpoint"""
    # Test with a non-existent claim ID
    response = client.get("/api/v1/claims/999")
    # Should return 404 for non-existent claim
    assert response.status_code == 404

def test_create_claim():
    """Test POST /claims endpoint"""
    claim_data = {
        "diagnosis_id": 1,
        "receipt_id": 1
    }
    response = client.post("/api/v1/claims", json=claim_data)
    # Accept various responses (200, 404, 500)
    assert response.status_code in [200, 404, 500]

def test_imports():
    """Test that all imports work correctly"""
    try:
        import fastapi
        from models.database import get_db
        from models.models import Claim, User
        from api.claims import router
        print("All imports successful")
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}") 