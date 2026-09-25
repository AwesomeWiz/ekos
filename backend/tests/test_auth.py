from auth.security import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing_and_verification():
    password = "SecretPassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_generation_and_validation():
    payload = {"user_id": "user-uuid-123", "role": "Developer", "organization": "ABC Solutions"}
    token = create_access_token(payload)
    
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["user_id"] == "user-uuid-123"
    assert decoded["role"] == "Developer"
    assert decoded["organization"] == "ABC Solutions"

def test_login_valid_credentials(client):
    response = client.post("/api/login", json={
        "email": "arnold@aekos.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    response = client.post("/api/login", json={
        "email": "arnold@aekos.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "detail" in response.json()
