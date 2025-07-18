import pytest
from utils.auth import get_password_hash, verify_password, create_access_token

def test_password_hash_and_verify():
    pw = "testpw123"
    hashed = get_password_hash(pw)
    assert verify_password(pw, hashed)
    assert not verify_password("wrongpw", hashed)

def test_create_access_token():
    token = create_access_token(data={"sub": "testuser"})
    assert isinstance(token, str)