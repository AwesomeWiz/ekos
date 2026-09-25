import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    resource = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)

    # Relationship
    role = relationship("Role", back_populates="permissions")
