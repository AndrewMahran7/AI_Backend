"""add query_logs table

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-01 00:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("query_type", sa.String(32), nullable=False),
        sa.Column("classification_confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("retrieved_record_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("answer_confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("sources", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_logs_query_type", "query_logs", ["query_type"])


def downgrade() -> None:
    op.drop_index("ix_query_logs_query_type", table_name="query_logs")
    op.drop_table("query_logs")
