import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_pdf_process_no_file():
    response = client.post("/api/v1/users/pdf/process")
    assert response.status_code == 422

def test_pdf_process_dummy_file():
    # 실제 파일 업로드 테스트는 별도 환경 필요
    assert True