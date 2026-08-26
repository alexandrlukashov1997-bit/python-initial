from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from baseproject.db.base import Base
from baseproject.models.car_enums import (
    BodyType,
    CarStatus,
    DriveType,
    EngineType,
    TransmissionType,
)


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    seller_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    brand_id: Mapped[UUID] = mapped_column(
        ForeignKey("car_brands.id", ondelete="RESTRICT"),
        index=True,
    )
    model_id: Mapped[UUID] = mapped_column(
        ForeignKey("car_models.id", ondelete="RESTRICT"),
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer)
    mileage: Mapped[int] = mapped_column(Integer)
    vin: Mapped[str | None] = mapped_column(String(17), unique=True, nullable=True)
    body_type: Mapped[BodyType] = mapped_column(String(16))
    engine_type: Mapped[EngineType] = mapped_column(String(16))
    engine_size: Mapped[Decimal] = mapped_column(Numeric(3, 1))
    drive: Mapped[DriveType] = mapped_column(String(8))
    transmission: Mapped[TransmissionType] = mapped_column(String(16))
    color: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    warranty_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CarStatus] = mapped_column(
        String(16),
        default=CarStatus.DRAFT,
        server_default=CarStatus.DRAFT.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
