"""Workflow metadata models for content lifecycle."""

from sqlalchemy import Column, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.database import Base


class Topic(Base):
    __tablename__ = "workflow_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True)
    path = Column(String(512), nullable=False, unique=True)
    stage = Column(String(50), nullable=False, default="topics")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ResearchBrief(Base):
    __tablename__ = "workflow_research_briefs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False, unique=True)
    stage = Column(String(50), nullable=False, default="research")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Draft(Base):
    __tablename__ = "workflow_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False, unique=True)
    stage = Column(String(50), nullable=False, default="drafts")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Rewrite(Base):
    __tablename__ = "workflow_rewrites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False, unique=True)
    stage = Column(String(50), nullable=False, default="rewrites")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PublishedArticle(Base):
    __tablename__ = "workflow_published_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False, unique=True)
    stage = Column(String(50), nullable=False, default="published")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LandingPage(Base):
    __tablename__ = "workflow_landing_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False, unique=True)
    stage = Column(String(50), nullable=False, default="landing-pages")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditRun(Base):
    __tablename__ = "workflow_audit_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path = Column(String(512), nullable=False, unique=True)
    stage = Column(String(50), nullable=False)
    latest_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
