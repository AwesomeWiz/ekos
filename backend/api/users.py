from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.dependencies import require_admin
from auth.security import hash_password
from models.base import get_db
from models.role import Role
from models.user import User
from schemas.user import RoleRead, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["User Management"])


def _role(db: Session, role_id: str) -> Role:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Select an existing role")
    return role


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(User).filter(User.organization_id == admin.organization_id).order_by(User.full_name, User.id).all()


@router.get("/roles", response_model=list[RoleRead])
def list_roles(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(Role).order_by(Role.role_name).all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    role = _role(db, body.role_id)
    email = str(body.email).lower()
    if db.query(User.id).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(full_name=body.full_name, email=email, password_hash=hash_password(body.password),
                role_id=role.id, organization_id=admin.organization_id, status=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from error
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: str, body: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id, User.organization_id == admin.organization_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = _role(db, body.role_id) if body.role_id is not None else None
    if user.id == admin.id and (body.status is False or (role and role.role_name != "Administrator")):
        raise HTTPException(status_code=400, detail="You cannot disable your own account or remove your own admin role")
    if role:
        user.role_id = role.id
    if body.status is not None:
        user.status = body.status
    db.commit()
    db.refresh(user)
    return user
