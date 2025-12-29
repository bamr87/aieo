"""Audit model."""
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from ..core.database import Base


class Audit(Base):
    """Audit result model."""
    
    __tablename__ = "audits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    content_hash = Column(String(64), nullable=False, index=True)
    url = Column(String, nullable=True)
    score = Column(Integer, nullable=False)  # 0-100
    grade = Column(String(2), nullable=False)
    gaps = Column(JSON, default=[], nullable=False)
    fixes = Column(JSON, default=[], nullable=False)
    benchmark = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Cache expiration
    
    # Relationships
    user = relationship("User", backref="audits")


