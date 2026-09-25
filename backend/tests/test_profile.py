def test_profile_unauthorized_without_jwt(client):
    response = client.get("/api/profile")
    assert response.status_code == 403 or response.status_code == 401

def test_profile_authorized_with_jwt(client):
    # Login first
    login_resp = client.post("/api/login", json={
        "email": "arnold@aekos.com",
        "password": "password123"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/profile", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "arnold@aekos.com"
    assert data["full_name"] == "Arnold Shibu"
    assert data["role"] == "Developer"
    assert data["organization"] == "ABC Solutions"
    assert "password_hash" not in data
