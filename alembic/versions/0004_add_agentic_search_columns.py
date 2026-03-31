"""Add agentic search columns to query_logs.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers used by Alembic.
revision: str = "0004"
down_revision: str = "0003"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "query_logs",
        sa.Column(
            "iterations",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "query_logs",
        sa.Column(
            "used_agentic_search",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "query_logs",
        sa.Column(
            "agentic_search_queries",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("query_logs", "agentic_search_queries")
    op.drop_column("query_logs", "used_agentic_search")
    op.drop_column("query_logs", "iterations")
