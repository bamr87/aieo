"""Workflow metadata tables.

Revision ID: 002
Revises: 001
Create Date: 2026-04-22 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def _create_table(name: str):
    op.create_table(
        name,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False, unique=True),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(f"idx_{name}_path", name, ["path"])
    op.create_index(f"idx_{name}_stage", name, ["stage"])


def upgrade() -> None:
    _create_table("workflow_topics")
    # Topic.title is indexed in the ORM model.
    op.create_index("idx_workflow_topics_title", "workflow_topics", ["title"])
    _create_table("workflow_research_briefs")
    _create_table("workflow_drafts")
    _create_table("workflow_rewrites")
    _create_table("workflow_published_articles")
    _create_table("workflow_landing_pages")
    op.create_table(
        "workflow_audit_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("path", sa.String(length=512), nullable=False, unique=True),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("latest_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_workflow_audit_runs_path", "workflow_audit_runs", ["path"])
    op.create_index("idx_workflow_audit_runs_stage", "workflow_audit_runs", ["stage"])


def downgrade() -> None:
    op.drop_table("workflow_audit_runs")
    op.drop_table("workflow_landing_pages")
    op.drop_table("workflow_published_articles")
    op.drop_table("workflow_rewrites")
    op.drop_table("workflow_drafts")
    op.drop_table("workflow_research_briefs")
    op.drop_table("workflow_topics")
