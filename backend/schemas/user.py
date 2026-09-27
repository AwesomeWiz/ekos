from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

class UserProfileResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: Optional[str] = None
    organization: Optional[str] = None
    permissions: list["PermissionRead"] = []

    model_config = ConfigDict(from_attributes=True)


class PermissionRead(BaseModel):
    resource: str
    action: str

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role_id: Optional[str] = None
    organization_id: Optional[str] = None

class UserRead(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role_id: Optional[str] = None
    organization_id: Optional[str] = None
    status: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
