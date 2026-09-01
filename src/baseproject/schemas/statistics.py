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


class SalesStatisticsBucket(BaseModel):
    period_start: datetime
    units_sold: int
    revenue: Decimal


class SalesStatisticsTotals(BaseModel):
    units_sold: int
    revenue: Decimal


class SalesStatisticsFilters(BaseModel):
    brand_id: UUID | None
    model_id: UUID | None
    seller_id: UUID | None
    date_from: date | None
    date_till: date | None


class SalesStatisticsResponse(BaseModel):
    granularity: SalesGranularity
    filters: SalesStatisticsFilters
    buckets: list[SalesStatisticsBucket]
    totals: SalesStatisticsTotals
