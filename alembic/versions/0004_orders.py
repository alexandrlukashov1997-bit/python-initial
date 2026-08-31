"""orders and order_items tables

Revision ID: 0004_orders
Revises: 0003_car_catalog
Create Date: 2026-08-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_orders"
down_revision: str | None = "0003_car_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(length=12), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("customer_first_name", sa.String(length=100), nullable=False),
        sa.Column("customer_last_name", sa.String(length=100), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("additional_info", sa.Text(), nullable=True),
        sa.Column("warranty", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number"),
    )
    op.create_index(op.f("ix_orders_order_number"), "orders", ["order_number"], unique=True)
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("car_id", sa.Uuid(), nullable=False),
        sa.Column("brand_name", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("body_type", sa.String(length=16), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["car_id"], ["cars.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_car_id"), "order_items", ["car_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_order_items_car_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_order_number"), table_name="orders")
    op.drop_table("orders")
