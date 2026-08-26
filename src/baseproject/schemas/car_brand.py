from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CarBrandCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CarBrandPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime


class CarModelCreateRequest(BaseModel):
    brand_id: UUID
    name: str = Field(min_length=1, max_length=100)


class CarModelPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand_id: UUID
    name: str
    created_at: datetime
