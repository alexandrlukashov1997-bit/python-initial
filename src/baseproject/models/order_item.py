from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from baseproject.db.base import Base
from baseproject.models.car_enums import BodyType


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
    )
    car_id: Mapped[UUID] = mapped_column(
        ForeignKey("cars.id", ondelete="RESTRICT"),
        index=True,
    )
    brand_name: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str] = mapped_column(String(100))
    body_type: Mapped[BodyType] = mapped_column(String(16))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
