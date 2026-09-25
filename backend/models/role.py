import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
from models.base import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Relationships
    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", back_populates="role", cascade="all, delete-orphan")
