# AEKOS Backend Foundation

The backend for AEKOS (Autonomous Enterprise Knowledge Operating System), built with Python 3.11+, FastAPI, SQLAlchemy, Pydantic, and JWT authentication.

---

## 1. Prerequisites

- Python 3.11+
- PostgreSQL 16+ (or default SQLite for local development/testing)

---

## 2. Environment Setup

### Create and Activate Virtual Environment

```bash
# Navigate to the backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configuration (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Configure your environment variables as needed:

```env
JWT_SECRET=your-secure-jwt-secret-key
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/aekos_db
```

*(Note: If `POSTGRES_URL` is omitted or set to SQLite, the application defaults to an SQLite file database `sqlite:///./aekos.db` for instant out-of-the-box local testing).*

---

## 4. Database Setup (PostgreSQL)

If using PostgreSQL:

1. Ensure PostgreSQL service is running on port 5432.
2. Create the database `aekos_db`:
   ```sql
   CREATE DATABASE aekos_db;
   ```
3. Update `POSTGRES_URL` in `.env`:
   ```env
   POSTGRES_URL=postgresql://username:password@localhost:5432/aekos_db
   ```
4. Tables and default roles/users will be auto-initialized when starting the FastAPI backend application.

---

## 5. Running the Backend Server

```bash
uvicorn main:app --reload
```

The API server will run at:
- **Base API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 6. Default Seed Credentials

Upon initial startup, default roles and test accounts are seeded automatically:

| Full Name | Email | Password | Role | Organization |
| :--- | :--- | :--- | :--- | :--- |
| **Arnold Shibu** | `arnold@aekos.com` | `password123` | Developer | ABC Solutions |
| **System Admin** | `admin@aekos.com` | `admin123` | Administrator | ABC Solutions |

---

## 7. Running Tests

Execute the automated pytest suite:

```bash
pytest
```

---

## 8. Example API Requests

### Login (`POST /api/login`)

**PowerShell:**
```powershell
$body = @{
    email = "arnold@aekos.com"
    password = "password123"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/login" -Method Post -ContentType "application/json" -Body $body
$token = $response.access_token
Write-Host "JWT Access Token: $token"
```

**cURL:**
```bash
curl -X POST "http://localhost:8000/api/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "arnold@aekos.com", "password": "password123"}'
```

---

### Retrieve User Profile (`GET /api/profile`)

**PowerShell:**
```powershell
$headers = @{
    Authorization = "Bearer $token"
}
Invoke-RestMethod -Uri "http://localhost:8000/api/profile" -Method Get -Headers $headers
```

**cURL:**
```bash
curl -X GET "http://localhost:8000/api/profile" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

---

### Register a Connector (`POST /api/connectors`)

**PowerShell:**
```powershell
$connectorBody = @{
    name = "AEKOS GitHub Repo"
    type = "GitHub"
    configuration = @{
        api_url = "https://api.github.com"
        token = "ghp_exampletoken123"
        sync_interval = "1 hour"
    }
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://localhost:8000/api/connectors" -Method Post -ContentType "application/json" -Headers $headers -Body $connectorBody
```

**cURL:**
```bash
curl -X POST "http://localhost:8000/api/connectors" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
     -d '{
       "name": "AEKOS GitHub Repo",
       "type": "GitHub",
       "configuration": {
         "api_url": "https://api.github.com",
         "token": "ghp_exampletoken123",
         "sync_interval": "1 hour"
       }
     }'
```
