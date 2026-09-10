"""Esquema inicial portfolio + chat

Revision ID: 001_initial
Revises:
Create Date: 2026-09-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tech_stack", sa.String(length=300), nullable=True),
        sa.Column("live_url", sa.String(length=500), nullable=True),
        sa.Column("repo_url", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="live", nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="100", nullable=False),
        sa.Column("visits", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)

    op.create_table(
        "chat_sessions",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("flow_state", sa.String(length=32), nullable=False),
        sa.Column("messages_json", sa.Text(), nullable=False),
        sa.Column("project_type", sa.String(length=64), nullable=True),
        sa.Column("scope_summary", sa.Text(), nullable=True),
        sa.Column("estimated_range_usd", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.create_table(
        "quote_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("project_type", sa.String(length=64), nullable=False),
        sa.Column("scope_summary", sa.Text(), nullable=False),
        sa.Column("estimated_range_usd", sa.String(length=64), nullable=False),
        sa.Column("client_name", sa.String(length=200), nullable=True),
        sa.Column("client_email", sa.String(length=320), nullable=False),
        sa.Column("client_phone", sa.String(length=32), nullable=True),
        sa.Column("client_budget", sa.String(length=64), nullable=True),
        sa.Column("preferred_channel", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quote_leads_id"), "quote_leads", ["id"], unique=False)
    op.create_index(op.f("ix_quote_leads_session_id"), "quote_leads", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_quote_leads_session_id"), table_name="quote_leads")
    op.drop_index(op.f("ix_quote_leads_id"), table_name="quote_leads")
    op.drop_table("quote_leads")
    op.drop_table("chat_sessions")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")
