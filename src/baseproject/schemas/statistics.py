from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class SalesGranularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class SalesGroupBy(StrEnum):
    BRAND = "brand"
    MODEL = "model"
    SELLER = "seller"
    BODY_TYPE = "body_type"


class SalesStatisticsBucket(BaseModel):
    period_start: datetime | None = None
    group_key: str | None = None
    group_id: UUID | None = None
    units_sold: int
    revenue: Decimal
    order_count: int
    avg_order_value: Decimal | None = None
    avg_unit_price: Decimal | None = None


class SalesStatisticsTotals(BaseModel):
    units_sold: int
    revenue: Decimal
    order_count: int
    avg_order_value: Decimal | None = None
    avg_unit_price: Decimal | None = None


class SalesStatisticsFilters(BaseModel):
    brand_id: UUID | None
    model_id: UUID | None
    seller_id: UUID | None
    date_from: date | None
    date_till: date | None
    group_by: SalesGroupBy | None = None


class SalesStatisticsResponse(BaseModel):
    granularity: SalesGranularity | None = None
    group_by: SalesGroupBy | None = None
    filters: SalesStatisticsFilters
    buckets: list[SalesStatisticsBucket]
    totals: SalesStatisticsTotals


class OrderStatusCount(BaseModel):
    status: str
    count: int


class OrderStatisticsFilters(BaseModel):
    seller_id: UUID | None
    date_from: date | None
    date_till: date | None


class OrderStatisticsResponse(BaseModel):
    filters: OrderStatisticsFilters
    orders_by_status: list[OrderStatusCount]
    cancellation_rate: Decimal | None
    completion_rate: Decimal | None
    pending_pipeline_value: Decimal


class InventoryBrandBreakdown(BaseModel):
    brand_id: UUID
    count: int


class InventoryStatisticsFilters(BaseModel):
    seller_id: UUID | None


class InventoryStatisticsResponse(BaseModel):
    filters: InventoryStatisticsFilters
    active_listings: int
    sold_inventory: int
    avg_listing_price: Decimal | None
    by_brand: list[InventoryBrandBreakdown]
