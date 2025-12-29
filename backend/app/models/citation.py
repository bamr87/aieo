"""Citation model."""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.database import Base


class Citation(Base):
    """Citation model (TimescaleDB hypertable)."""

    __tablename__ = "citations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    engine = Column(String(20), nullable=False, index=True)
    prompt = Column(String, nullable=False)
    prompt_category = Column(String(50), nullable=True)
    citation_text = Column(String, nullable=False)
    position = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)  # 0-1
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    verified = Column(Boolean, default=False, nullable=False)
