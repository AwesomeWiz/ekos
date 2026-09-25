from fastapi import APIRouter, Depends
from models.user import User
from schemas.user import UserProfileResponse
from auth.dependencies import get_current_user

router = APIRouter(tags=["User Profile"])

@router.get("/profile", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Retrieve authenticated user basic profile context."""
    role_name = current_user.role.role_name if current_user.role else "Guest"
    org_name = current_user.organization.name if current_user.organization else ""
    
    return UserProfileResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        role=role_name,
        organization=org_name
    )
