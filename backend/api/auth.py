from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.base import get_db
from schemas.auth import LoginRequest, TokenResponse
from services.auth_service import authenticate_user, create_user_token

router = APIRouter(tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email and password, returning JWT access token."""
    user = authenticate_user(db, email=request.email, password=request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_user_token(user)
    return TokenResponse(access_token=access_token, token_type="bearer")

@router.post("/logout")
def logout():
    """Client logout endpoint. Note that JWT tokens are stateless."""
    return {
        "message": "Logged out successfully.",
        "details": "JWT tokens are stateless. The client should remove the stored access token from localStorage/cookies."
    }
