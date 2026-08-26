from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from baseproject.models.car_enums import (
    BodyType,
    CarStatus,
    DriveType,
    EngineType,
    TransmissionType,
)

_MIN_YEAR = 1980


class CarPhotoCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False


class CarPhotoPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    car_id: UUID
    url: str
    sort_order: int
    is_primary: bool


class CarCreateRequest(BaseModel):
    brand_id: UUID
    model_id: UUID
    year: int = Field(ge=_MIN_YEAR)
    mileage: int = Field(ge=0)
    vin: str | None = Field(default=None, min_length=17, max_length=17)
    body_type: BodyType
    engine_type: EngineType
    engine_size: Decimal = Field(gt=0, max_digits=3, decimal_places=1)
    drive: DriveType
    transmission: TransmissionType
    color: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    warranty_months: int | None = Field(default=None, ge=0)
    description: str | None = None
    status: CarStatus = CarStatus.DRAFT

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        current_year = datetime.now().year
        if value > current_year:
            msg = f"Year must not exceed {current_year}"
            raise ValueError(msg)
        return value


class CarUpdateRequest(BaseModel):
    brand_id: UUID | None = None
    model_id: UUID | None = None
    year: int | None = Field(default=None, ge=_MIN_YEAR)
    mileage: int | None = Field(default=None, ge=0)
    vin: str | None = Field(default=None, min_length=17, max_length=17)
    body_type: BodyType | None = None
    engine_type: EngineType | None = None
    engine_size: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=3,
        decimal_places=1,
    )
    drive: DriveType | None = None
    transmission: TransmissionType | None = None
    color: str | None = Field(default=None, min_length=1, max_length=50)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    warranty_months: int | None = Field(default=None, ge=0)
    description: str | None = None
    status: CarStatus | None = None

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int | None) -> int | None:
        if value is None:
            return value
        current_year = datetime.now().year
        if value > current_year:
            msg = f"Year must not exceed {current_year}"
            raise ValueError(msg)
        return value


class CarPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    brand_id: UUID
    model_id: UUID
    year: int
    mileage: int
    vin: str | None
    body_type: str
    engine_type: str
    engine_size: Decimal
    drive: str
    transmission: str
    color: str
    price: Decimal
    warranty_months: int | None
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class CarDetailPublic(CarPublic):
    photos: list[CarPhotoPublic] = Field(default_factory=list)


class CarListResponse(BaseModel):
    items: list[CarPublic]
    total: int
    limit: int
    offset: int
