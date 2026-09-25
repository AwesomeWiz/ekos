from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from models.base import engine, Base, SessionLocal
from models.organization import Organization
from models.role import Role
from models.permission import Permission
from models.user import User
from models.connector import Connector, ConnectorConfiguration
from auth.security import hash_password

from api.auth import router as auth_router
from api.profile import router as profile_router
from api.connectors import router as connectors_router

def init_db(target_engine=None):
    """Create database tables and seed initial default data."""
    bind_engine = target_engine or engine
    Base.metadata.create_all(bind=bind_engine)
    
    db: Session = sessionmaker(autocommit=False, autoflush=False, bind=bind_engine)() if target_engine else SessionLocal()
    try:
        # Seed Roles
        default_roles = [
            ("Administrator", "Full system administrative access"),
            ("Manager", "Management access to project and team knowledge"),
            ("Developer", "Development access to code and technical knowledge"),
            ("HR", "Human resources and personnel documentation access"),
            ("Guest", "Restricted read-only access")
        ]
        
        roles_map = {}
        for role_name, desc in default_roles:
            role = db.query(Role).filter(Role.role_name == role_name).first()
            if not role:
                role = Role(role_name=role_name, description=desc)
                db.add(role)
                db.flush()
            roles_map[role_name] = role

        # Seed Default Organization
        org = db.query(Organization).filter(Organization.name == "ABC Solutions").first()
        if not org:
            org = Organization(name="ABC Solutions", domain="abcsolutions.com")
            db.add(org)
            db.flush()

        # Seed Default Users if empty
        user_count = db.query(User).count()
        if user_count == 0:
            dev_user = User(
                full_name="Arnold Shibu",
                email="arnold@aekos.com",
                password_hash=hash_password("password123"),
                role_id=roles_map["Developer"].id,
                organization_id=org.id,
                status=True
            )
            admin_user = User(
                full_name="System Admin",
                email="admin@aekos.com",
                password_hash=hash_password("admin123"),
                role_id=roles_map["Administrator"].id,
                organization_id=org.id,
                status=True
            )
            db.add(dev_user)
            db.add(admin_user)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    yield
    # Shutdown logic

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Enterprise Knowledge Operating System - Backend API Foundation",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(profile_router, prefix=settings.API_PREFIX)
app.include_router(connectors_router, prefix=settings.API_PREFIX)

@app.get("/")
def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
