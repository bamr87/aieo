"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("email_verified", sa.Boolean(), default=False, nullable=False),
        sa.Column("plan", sa.String(20), default="free", nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("settings", sa.JSON(), default={}, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # Create audits table
    op.create_table(
        "audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("grade", sa.String(2), nullable=False),
        sa.Column("gaps", sa.JSON(), default=[], nullable=False),
        sa.Column("fixes", sa.JSON(), default=[], nullable=False),
        sa.Column("benchmark", sa.JSON(), default={}, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_audits_user_id", "audits", ["user_id"])
    op.create_index("idx_audits_content_hash", "audits", ["content_hash"])
    op.create_index("idx_audits_created_at", "audits", ["created_at"])

    # Create citations table (will be converted to TimescaleDB hypertable)
    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("engine", sa.String(20), nullable=False),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("prompt_category", sa.String(50), nullable=True),
        sa.Column("citation_text", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified", sa.Boolean(), default=False, nullable=False),
    )
    op.create_index("idx_citations_url", "citations", ["url"])
    op.create_index("idx_citations_domain", "citations", ["domain"])
    op.create_index("idx_citations_engine", "citations", ["engine"])
    op.create_index("idx_citations_detected_at", "citations", ["detected_at"])

    # Convert citations to TimescaleDB hypertable (if TimescaleDB extension is available)
    # Note: This will fail if TimescaleDB extension is not installed, which is OK for MVP
    try:
        op.execute(
            "SELECT create_hypertable('citations', 'detected_at', if_not_exists => TRUE);"
        )
    except Exception:
        # TimescaleDB not available, continue without hypertable
        pass


def downgrade() -> None:
    op.drop_table("citations")
    op.drop_table("audits")
    op.drop_table("users")
