from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class OrganizationCreate(BaseModel):
    name: str
    domain: Optional[str] = None

class OrganizationRead(BaseModel):
    id: str
    name: str
    domain: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
