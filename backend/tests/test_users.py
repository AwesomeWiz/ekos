import pytest

from auth.security import create_access_token, verify_password
from models.organization import Organization
from models.role import Role
from models.user import User


def login(client, email="admin@aekos.com", password="admin123"):
    response = client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def body(db, **changes):
    return {"full_name": "New Developer", "email": "employee@example.com", "password": "password123",
            "role_id": db.query(Role).filter(Role.role_name == "Developer").one().id, **changes}


@pytest.mark.parametrize("method,path", [("get", "/api/users"), ("get", "/api/users/roles"),
                                        ("post", "/api/users"), ("put", "/api/users/any")])
def test_non_admin_cannot_manage_users(client, db, method, path):
    user = db.query(User).filter(User.email == "arnold@aekos.com").one()
    # Even a valid signed token claiming Administrator cannot override the persisted role.
    headers = {"Authorization": f"Bearer {create_access_token({'sub': user.id, 'role': 'Administrator'})}"}
    response = getattr(client, method)(path, headers=headers, **({"json": body(db)} if method == "post" else {"json": {"status": False}} if method == "put" else {}))
    assert response.status_code == 403


def test_user_management_requires_authentication(client):
    assert client.get("/api/users").status_code == 401


def test_create_employee_reuses_roles_hashing_and_organization(client, db):
    headers = login(client)
    roles = client.get("/api/users/roles", headers=headers)
    assert roles.status_code == 200
    assert {role["role_name"] for role in roles.json()} == {"Administrator", "Manager", "Developer", "HR", "Guest"}
    response = client.post("/api/users", headers=headers, json=body(db, organization_id="untrusted-org"))
    assert response.status_code == 201
    data = response.json()
    admin = db.query(User).filter(User.email == "admin@aekos.com").one()
    assert data["organization_id"] == admin.organization_id
    assert data["status"] is True
    assert "password" not in data and "password_hash" not in data
    user = db.query(User).filter(User.id == data["id"]).one()
    assert verify_password("password123", user.password_hash)
    assert user.role.role_name == "Developer"
    assert any(item["id"] == user.id for item in client.get("/api/users", headers=headers).json())
    employee_headers = login(client, "employee@example.com", "password123")
    assert client.get("/api/profile", headers=employee_headers).json()["role"] == "Developer"


def test_role_status_updates_apply_to_existing_tokens(client, db):
    headers = login(client)
    employee = db.query(User).filter(User.email == "arnold@aekos.com").one()
    employee_headers = login(client, "arnold@aekos.com", "password123")
    manager = db.query(Role).filter(Role.role_name == "Manager").one()
    response = client.put(f"/api/users/{employee.id}", headers=headers, json={"role_id": manager.id})
    assert response.status_code == 200
    assert client.get("/api/profile", headers=employee_headers).json()["role"] == "Manager"
    assert client.put(f"/api/users/{employee.id}", headers=headers, json={"status": False}).json()["status"] is False
    assert client.get("/api/profile", headers=employee_headers).status_code == 403
    assert client.post("/api/login", json={"email": employee.email, "password": "password123"}).status_code == 401
    assert client.put(f"/api/users/{employee.id}", headers=headers, json={"status": True}).json()["status"] is True
    assert client.get("/api/profile", headers=employee_headers).status_code == 200


def test_users_are_scoped_to_admin_organization(client, db):
    headers = login(client)
    other = Organization(name="Other organization")
    db.add(other); db.flush()
    employee = db.query(User).filter(User.email == "arnold@aekos.com").one()
    employee.organization_id = other.id
    db.commit()
    assert employee.id not in [user["id"] for user in client.get("/api/users", headers=headers).json()]
    assert client.put(f"/api/users/{employee.id}", headers=headers, json={"status": False}).status_code == 404
    assert employee.status is True


def test_duplicate_email_and_invalid_roles(client, db):
    headers = login(client)
    assert client.post("/api/users", headers=headers, json=body(db, email="ARNOLD@aekos.com")).status_code == 409
    assert client.post("/api/users", headers=headers, json=body(db, role_id="missing")).status_code == 400
    employee = db.query(User).filter(User.email == "arnold@aekos.com").one()
    assert client.put(f"/api/users/{employee.id}", headers=headers, json={"role_id": "missing"}).status_code == 400
    assert client.put("/api/users/missing", headers=headers, json={"status": False}).status_code == 404


@pytest.mark.parametrize("changes", [{"full_name": "  "}, {"password": "short"}, {"password": "é" * 40}, {"email": "invalid"}, {"role_id": ""}])
def test_create_user_validation(client, db, changes):
    assert client.post("/api/users", headers=login(client), json=body(db, **changes)).status_code == 422


def test_update_validation_and_self_lockout_protection(client, db):
    headers = login(client)
    admin = db.query(User).filter(User.email == "admin@aekos.com").one()
    for update in [{}, {"status": None}, {"role_id": None}, {"organization_id": "other"}]:
        assert client.put(f"/api/users/{admin.id}", headers=headers, json=update).status_code == 422
    assert client.put(f"/api/users/{admin.id}", headers=headers, json={"status": False}).status_code == 400
    assert client.put(f"/api/users/{admin.id}", headers=headers, json={"role_id": body(db)["role_id"]}).status_code == 400
    # A role revoked in the database immediately invalidates admin access with an old JWT.
    admin.role_id = body(db)["role_id"]
    db.commit()
    assert client.get("/api/users", headers=headers).status_code == 403
