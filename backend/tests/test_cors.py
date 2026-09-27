import pytest


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5173", "http://localhost:5173"])
def test_local_frontend_bearer_preflight(client, origin):
    response = client.options("/api/connectors", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers


def test_unconfigured_origin_is_rejected(client):
    response = client.options("/api/connectors", headers={
        "Origin": "https://unconfigured.example",
        "Access-Control-Request-Method": "GET",
    })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
