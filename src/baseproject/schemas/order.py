from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from baseproject.models.order_enums import OrderStatus


class OrderItemCreateRequest(BaseModel):
    car_id: UUID
    quantity: int = Field(ge=1)


class OrderCreateRequest(BaseModel):
    items: list[OrderItemCreateRequest] = Field(min_length=1)
    customer_first_name: str = Field(min_length=1, max_length=100)
    customer_last_name: str = Field(min_length=1, max_length=100)
    customer_email: EmailStr
    customer_phone: str = Field(min_length=1, max_length=32)
    additional_info: str | None = None
    warranty: str | None = None


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus


class OrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    car_id: UUID
    brand_name: str
    model_name: str
    body_type: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    user_id: UUID | None
    customer_first_name: str
    customer_last_name: str
    customer_email: str
    customer_phone: str
    additional_info: str | None
    warranty: str | None
    status: str
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class OrderDetailPublic(OrderPublic):
    items: list[OrderItemPublic]


class OrderListResponse(BaseModel):
    items: list[OrderPublic]
    total: int
    limit: int
    offset: int
