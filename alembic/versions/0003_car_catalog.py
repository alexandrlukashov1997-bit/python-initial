"""car catalog tables and seed data

Revision ID: 0003_car_catalog
Revises: 0002_profile_reset_tokens
Create Date: 2026-08-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_car_catalog"
down_revision: str | None = "0002_profile_reset_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEED_BRANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Toyota", ("Camry", "Corolla", "RAV4")),
    ("BMW", ("3 Series", "5 Series", "X5")),
    ("Lada", ("Vesta", "Granta", "Niva")),
    ("Mercedes-Benz", ("C-Class", "E-Class", "GLC")),
    ("Volkswagen", ("Golf", "Passat", "Tiguan")),
)


def upgrade() -> None:
    op.create_table(
        "car_brands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_car_brands_name"), "car_brands", ["name"], unique=True)

    op.create_table(
        "car_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["car_brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "name", name="uq_car_models_brand_name"),
    )
    op.create_index(
        op.f("ix_car_models_brand_id"),
        "car_models",
        ["brand_id"],
        unique=False,
    )

    op.create_table(
        "cars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seller_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("mileage", sa.Integer(), nullable=False),
        sa.Column("vin", sa.String(length=17), nullable=True),
        sa.Column("body_type", sa.String(length=16), nullable=False),
        sa.Column("engine_type", sa.String(length=16), nullable=False),
        sa.Column("engine_size", sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column("drive", sa.String(length=8), nullable=False),
        sa.Column("transmission", sa.String(length=16), nullable=False),
        sa.Column("color", sa.String(length=50), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("warranty_months", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="draft",
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["brand_id"], ["car_brands.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_id"], ["car_models.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vin"),
    )
    op.create_index(op.f("ix_cars_brand_id"), "cars", ["brand_id"], unique=False)
    op.create_index(op.f("ix_cars_model_id"), "cars", ["model_id"], unique=False)
    op.create_index(op.f("ix_cars_seller_id"), "cars", ["seller_id"], unique=False)
    op.create_index(op.f("ix_cars_status"), "cars", ["status"], unique=False)

    op.create_table(
        "car_photos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("car_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["car_id"], ["cars.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_car_photos_car_id"),
        "car_photos",
        ["car_id"],
        unique=False,
    )

    for brand_name, model_names in _SEED_BRANDS:
        op.execute(
            sa.text(
                "INSERT INTO car_brands (id, name) VALUES (gen_random_uuid(), :name)"
            ).bindparams(name=brand_name)
        )
        for model_name in model_names:
            op.execute(
                sa.text(
                    "INSERT INTO car_models (id, brand_id, name) "
                    "SELECT gen_random_uuid(), id, :model_name "
                    "FROM car_brands WHERE name = :brand_name"
                ).bindparams(model_name=model_name, brand_name=brand_name)
            )


def downgrade() -> None:
    op.drop_index(op.f("ix_car_photos_car_id"), table_name="car_photos")
    op.drop_table("car_photos")
    op.drop_index(op.f("ix_cars_status"), table_name="cars")
    op.drop_index(op.f("ix_cars_seller_id"), table_name="cars")
    op.drop_index(op.f("ix_cars_model_id"), table_name="cars")
    op.drop_index(op.f("ix_cars_brand_id"), table_name="cars")
    op.drop_table("cars")
    op.drop_index(op.f("ix_car_models_brand_id"), table_name="car_models")
    op.drop_table("car_models")
    op.drop_index(op.f("ix_car_brands_name"), table_name="car_brands")
    op.drop_table("car_brands")
