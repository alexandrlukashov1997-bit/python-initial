from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from baseproject.core.exceptions import BadRequest
from baseproject.models.car import Car
from baseproject.models.order import Order
from baseproject.models.order_enums import OrderStatus
from baseproject.models.order_item import OrderItem
from baseproject.models.user import User, UserRole
from baseproject.schemas.statistics import (
    SalesGranularity,
    SalesStatisticsBucket,
    SalesStatisticsFilters,
    SalesStatisticsResponse,
    SalesStatisticsTotals,
)
from baseproject.services import car_catalog as catalog_service


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _date_range_conditions(
    date_from: date | None,
    date_till: date | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if date_from is not None:
        start = datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        conditions.append(Order.updated_at >= start)
    if date_till is not None:
        end = datetime.combine(
            date_till + timedelta(days=1),
            datetime.min.time(),
            tzinfo=UTC,
        )
        conditions.append(Order.updated_at < end)
    return conditions


async def _validate_filters(
    db: AsyncSession,
    *,
    brand_id: UUID | None,
    model_id: UUID | None,
    date_from: date | None,
    date_till: date | None,
) -> None:
    if date_from is not None and date_till is not None and date_from > date_till:
        raise BadRequest("date_from must be on or before date_till")

    if brand_id is not None and model_id is not None:
        await catalog_service.validate_brand_model_pair(db, brand_id, model_id)
    elif brand_id is not None:
        await catalog_service.get_brand(db, brand_id)
    elif model_id is not None:
        await catalog_service.get_model(db, model_id)


def _build_filter_conditions(
    user: User,
    *,
    brand_id: UUID | None,
    model_id: UUID | None,
    seller_id: UUID | None,
    date_from: date | None,
    date_till: date | None,
) -> tuple[list[ColumnElement[bool]], UUID | None]:
    conditions: list[ColumnElement[bool]] = [
        Order.status == OrderStatus.COMPLETED,
    ]

    effective_seller_id: UUID | None
    if _is_admin(user):
        effective_seller_id = seller_id
        if seller_id is not None:
            conditions.append(Car.seller_id == seller_id)
    else:
        effective_seller_id = user.id
        conditions.append(Car.seller_id == user.id)

    if brand_id is not None:
        conditions.append(Car.brand_id == brand_id)
    if model_id is not None:
        conditions.append(Car.model_id == model_id)

    conditions.extend(_date_range_conditions(date_from, date_till))
    return conditions, effective_seller_id


async def get_sales_statistics(
    db: AsyncSession,
    user: User,
    *,
    granularity: SalesGranularity,
    brand_id: UUID | None = None,
    model_id: UUID | None = None,
    seller_id: UUID | None = None,
    date_from: date | None = None,
    date_till: date | None = None,
) -> SalesStatisticsResponse:
    await _validate_filters(
        db,
        brand_id=brand_id,
        model_id=model_id,
        date_from=date_from,
        date_till=date_till,
    )

    conditions, effective_seller_id = _build_filter_conditions(
        user,
        brand_id=brand_id,
        model_id=model_id,
        seller_id=seller_id,
        date_from=date_from,
        date_till=date_till,
    )

    period_start = func.date_trunc(granularity.value, Order.updated_at).label(
        "period_start"
    )

    buckets_query = (
        select(
            period_start,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(OrderItem.line_total), 0).label("revenue"),
        )
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Car, Car.id == OrderItem.car_id)
        .where(*conditions)
        .group_by(period_start)
        .order_by(period_start)
    )

    bucket_rows = (await db.execute(buckets_query)).all()

    totals_query = (
        select(
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(OrderItem.line_total), 0).label("revenue"),
        )
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Car, Car.id == OrderItem.car_id)
        .where(*conditions)
    )
    totals_row = (await db.execute(totals_query)).one()

    return SalesStatisticsResponse(
        granularity=granularity,
        filters=SalesStatisticsFilters(
            brand_id=brand_id,
            model_id=model_id,
            seller_id=effective_seller_id,
            date_from=date_from,
            date_till=date_till,
        ),
        buckets=[
            SalesStatisticsBucket(
                period_start=row.period_start,
                units_sold=int(row.units_sold),
                revenue=Decimal(str(row.revenue)).quantize(Decimal("0.01")),
            )
            for row in bucket_rows
        ],
        totals=SalesStatisticsTotals(
            units_sold=int(totals_row.units_sold),
            revenue=Decimal(str(totals_row.revenue)).quantize(Decimal("0.01")),
        ),
    )
