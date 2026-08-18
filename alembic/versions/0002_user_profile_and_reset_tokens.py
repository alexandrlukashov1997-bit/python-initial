"""user profile fields, client role, password reset tokens

Revision ID: 0002_profile_reset_tokens
Revises: 0001_create_users
Create Date: 2026-08-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_profile_reset_tokens"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("first_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("phone", sa.String(length=32), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE users SET first_name = '', last_name = '', phone = '' "
            "WHERE first_name IS NULL"
        )
    )
    op.alter_column("users", "first_name", nullable=False)
    op.alter_column("users", "last_name", nullable=False)
    op.alter_column("users", "phone", nullable=False)

    op.execute(sa.text("UPDATE users SET role = 'client' WHERE role = 'user'"))
    op.alter_column(
        "users",
        "role",
        server_default="client",
        existing_type=sa.String(length=16),
        existing_nullable=False,
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_user_id"),
        "password_reset_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_password_reset_tokens_user_id"),
        table_name="password_reset_tokens",
    )
    op.drop_table("password_reset_tokens")

    op.alter_column(
        "users",
        "role",
        server_default="user",
        existing_type=sa.String(length=16),
        existing_nullable=False,
    )
    op.execute(sa.text("UPDATE users SET role = 'user' WHERE role = 'client'"))

    op.drop_column("users", "phone")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
