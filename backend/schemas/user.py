from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator

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
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role_id: str = Field(min_length=1)
    organization_id: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be empty")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class UserUpdate(BaseModel):
    role_id: Optional[str] = Field(default=None, min_length=1)
    status: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set or any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Provide a role_id or status; null values are not allowed")
        return self


class RoleRead(BaseModel):
    id: str
    role_name: str

    model_config = ConfigDict(from_attributes=True)

class UserRead(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role_id: Optional[str] = None
    organization_id: Optional[str] = None
    status: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
