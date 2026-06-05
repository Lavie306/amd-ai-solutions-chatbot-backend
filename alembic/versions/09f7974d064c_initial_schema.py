"""initial_schema

Revision ID: 09f7974d064c
Revises: 
Create Date: 2026-06-05 15:18:47.267974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09f7974d064c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the initial backend schema."""
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("contact", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="NEW"),
        sa.Column("lead_state", sa.Text(), nullable=False, server_default="IDLE"),
        sa.Column("fields", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("chat_log", sa.Text(), nullable=True, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id"),
    )

    op.create_table(
        "followup_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trigger_status", sa.Text(), nullable=False),
        sa.Column("delay_days", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("template", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="indexing"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "followup_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "lead_id",
            sa.Integer(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_id",
            sa.Integer(),
            sa.ForeignKey("followup_rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("scheduled", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("result_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop the initial backend schema."""
    op.drop_table("followup_jobs")
    op.drop_table("documents")
    op.drop_table("settings")
    op.drop_table("followup_rules")
    op.drop_table("leads")
