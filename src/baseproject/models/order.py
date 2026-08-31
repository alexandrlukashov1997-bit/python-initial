from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from baseproject.db.base import Base
from baseproject.models.order_enums import OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_number: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_first_name: Mapped[str] = mapped_column(String(100))
    customer_last_name: Mapped[str] = mapped_column(String(100))
    customer_email: Mapped[str] = mapped_column(String(255))
    customer_phone: Mapped[str] = mapped_column(String(32))
    additional_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    warranty: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        String(16),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
