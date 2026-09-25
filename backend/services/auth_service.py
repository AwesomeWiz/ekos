from typing import Optional
from sqlalchemy.orm import Session
from models.user import User
from auth.security import verify_password, create_access_token

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Verify user credentials against PostgreSQL data."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def create_user_token(user: User) -> str:
    """Generate JWT containing user claims (id, role, organization)."""
    role_name = user.role.role_name if user.role else "Guest"
    org_name = user.organization.name if user.organization else ""
    
    payload = {
        "user_id": user.id,
        "sub": user.id,
        "email": user.email,
        "role": role_name,
        "organization": org_name
    }
    return create_access_token(payload)
