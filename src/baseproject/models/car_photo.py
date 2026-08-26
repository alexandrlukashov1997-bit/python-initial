from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column

from baseproject.db.base import Base


class CarPhoto(Base):
    __tablename__ = "car_photos"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    car_id: Mapped[UUID] = mapped_column(
        ForeignKey("cars.id", ondelete="CASCADE"),
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2048))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
    )
