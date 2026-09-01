"""add orders.completed_at

Revision ID: 0005_order_completed_at
Revises: 0004_orders
Create Date: 2026-09-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_order_completed_at"
down_revision: str | None = "0004_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE orders SET completed_at = updated_at WHERE status = 'completed'"
        )
    )


def downgrade() -> None:
    op.drop_column("orders", "completed_at")
