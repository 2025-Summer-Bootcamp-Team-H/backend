import os
import pytest
from fastapi.testclient import TestClient
from main import app

def pytest_configure(config):
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY 환경변수가 없어 전체 테스트를 건너뜁니다.", allow_module_level=True)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c