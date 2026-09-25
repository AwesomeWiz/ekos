def test_connector_crud_workflow(client):
    # Authenticate
    login_resp = client.post("/api/login", json={
        "email": "arnold@aekos.com",
        "password": "password123"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Connector
    payload = {
        "name": "Primary GitHub Repository",
        "type": "GitHub",
        "configuration": {
            "api_url": "https://api.github.com",
            "token": "ghp_dummytoken123456",
            "sync_interval": "1 hour"
        }
    }
    create_resp = client.post("/api/connectors", json=payload, headers=headers)
    assert create_resp.status_code == 201
    connector_data = create_resp.json()
    connector_id = connector_data["id"]
    assert connector_data["name"] == "Primary GitHub Repository"
    assert connector_data["type"] == "GitHub"
    assert connector_data["status"] == "active"
    assert connector_data["configuration"]["api_url"] == "https://api.github.com"

    # 2. List Connectors
    list_resp = client.get("/api/connectors", headers=headers)
    assert list_resp.status_code == 200
    connectors = list_resp.json()
    assert len(connectors) == 1
    assert connectors[0]["id"] == connector_id

    # 3. Update Connector
    update_payload = {
        "name": "Updated GitHub Connector",
        "status": "paused",
        "configuration": {
            "sync_interval": "2 hours"
        }
    }
    update_resp = client.put(f"/api/connectors/{connector_id}", json=update_payload, headers=headers)
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["name"] == "Updated GitHub Connector"
    assert updated_data["status"] == "paused"
    assert updated_data["configuration"]["sync_interval"] == "2 hours"

    # 4. Delete Connector
    delete_resp = client.delete(f"/api/connectors/{connector_id}", headers=headers)
    assert delete_resp.status_code == 204

    # 5. Verify Deletion
    list_after_delete = client.get("/api/connectors", headers=headers)
    assert len(list_after_delete.json()) == 0
