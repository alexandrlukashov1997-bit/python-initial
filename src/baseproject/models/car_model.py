from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from baseproject.db.base import Base


class CarModel(Base):
    __tablename__ = "car_models"
    __table_args__ = (
        UniqueConstraint("brand_id", "name", name="uq_car_models_brand_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    brand_id: Mapped[UUID] = mapped_column(
        ForeignKey("car_brands.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
