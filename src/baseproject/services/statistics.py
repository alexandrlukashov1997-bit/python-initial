from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from baseproject.core.exceptions import BadRequest
from baseproject.models.car import Car
from baseproject.models.car_enums import CarStatus
from baseproject.models.order import Order
from baseproject.models.order_enums import OrderStatus
from baseproject.models.order_item import OrderItem
from baseproject.models.user import User, UserRole
from baseproject.schemas.statistics import (
    InventoryBrandBreakdown,
    InventoryStatisticsFilters,
    InventoryStatisticsResponse,
    OrderStatisticsFilters,
    OrderStatisticsResponse,
    OrderStatusCount,
    SalesGranularity,
    SalesGroupBy,
    SalesStatisticsBucket,
    SalesStatisticsFilters,
    SalesStatisticsResponse,
    SalesStatisticsTotals,
)
from baseproject.services import car_catalog as catalog_service


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _compute_derived_metrics(
    units_sold: int,
    revenue: Decimal,
    order_count: int,
) -> tuple[Decimal | None, Decimal | None]:
    avg_order_value = (
        _quantize_money(revenue / order_count) if order_count > 0 else None
    )
    avg_unit_price = (
        _quantize_money(revenue / units_sold) if units_sold > 0 else None
    )
    return avg_order_value, avg_unit_price


def _build_totals(
    units_sold: int,
    revenue: Decimal,
    order_count: int,
) -> SalesStatisticsTotals:
    avg_order_value, avg_unit_price = _compute_derived_metrics(
        units_sold, revenue, order_count
    )
    return SalesStatisticsTotals(
        units_sold=units_sold,
        revenue=_quantize_money(revenue),
        order_count=order_count,
        avg_order_value=avg_order_value,
        avg_unit_price=avg_unit_price,
    )


def _build_bucket(
    *,
    units_sold: int,
    revenue: Decimal,
    order_count: int,
    period_start: datetime | None = None,
    group_key: str | None = None,
    group_id: UUID | None = None,
) -> SalesStatisticsBucket:
    avg_order_value, avg_unit_price = _compute_derived_metrics(
        units_sold, revenue, order_count
    )
    return SalesStatisticsBucket(
        period_start=period_start,
        group_key=group_key,
        group_id=group_id,
        units_sold=units_sold,
        revenue=_quantize_money(revenue),
        order_count=order_count,
        avg_order_value=avg_order_value,
        avg_unit_price=avg_unit_price,
    )


def _completed_date_range_conditions(
    date_from: date | None,
    date_till: date | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if date_from is not None:
        start = datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        conditions.append(Order.completed_at >= start)
    if date_till is not None:
        end = datetime.combine(
            date_till + timedelta(days=1),
            datetime.min.time(),
            tzinfo=UTC,
        )
        conditions.append(Order.completed_at < end)
    return conditions


def _created_date_range_conditions(
    date_from: date | None,
    date_till: date | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if date_from is not None:
        start = datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        conditions.append(Order.created_at >= start)
    if date_till is not None:
        end = datetime.combine(
            date_till + timedelta(days=1),
            datetime.min.time(),
            tzinfo=UTC,
        )
        conditions.append(Order.created_at < end)
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


def _build_sales_filter_conditions(
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
        Order.completed_at.is_not(None),
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

    conditions.extend(_completed_date_range_conditions(date_from, date_till))
    return conditions, effective_seller_id


def _build_order_scope_conditions(
    user: User,
    *,
    seller_id: UUID | None,
    date_from: date | None,
    date_till: date | None,
) -> tuple[list[ColumnElement[bool]], UUID | None]:
    conditions: list[ColumnElement[bool]] = []

    effective_seller_id: UUID | None
    if _is_admin(user):
        effective_seller_id = seller_id
        if seller_id is not None:
            conditions.append(Car.seller_id == seller_id)
    else:
        effective_seller_id = user.id
        conditions.append(Car.seller_id == user.id)

    conditions.extend(_created_date_range_conditions(date_from, date_till))
    return conditions, effective_seller_id


def _truncate_to_period(dt: datetime, granularity: SalesGranularity) -> datetime:
    normalized = dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    normalized = normalized.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == SalesGranularity.DAY:
        return normalized
    if granularity == SalesGranularity.WEEK:
        return normalized - timedelta(days=normalized.weekday())
    if granularity == SalesGranularity.MONTH:
        return normalized.replace(day=1)
    return normalized.replace(month=1, day=1)


def _next_period_start(
    current: datetime,
    granularity: SalesGranularity,
) -> datetime:
    if granularity == SalesGranularity.DAY:
        return current + timedelta(days=1)
    if granularity == SalesGranularity.WEEK:
        return current + timedelta(weeks=1)
    if granularity == SalesGranularity.MONTH:
        if current.month == 12:
            return current.replace(year=current.year + 1, month=1)
        return current.replace(month=current.month + 1)
    return current.replace(year=current.year + 1)


def _generate_period_starts(
    date_from: date,
    date_till: date,
    granularity: SalesGranularity,
) -> list[datetime]:
    start = _truncate_to_period(
        datetime.combine(date_from, datetime.min.time(), tzinfo=UTC),
        granularity,
    )
    end = _truncate_to_period(
        datetime.combine(date_till, datetime.min.time(), tzinfo=UTC),
        granularity,
    )
    periods: list[datetime] = []
    current = start
    while current <= end:
        periods.append(current)
        current = _next_period_start(current, granularity)
    return periods


def _zero_fill_buckets(
    bucket_rows: list[SalesStatisticsBucket],
    *,
    date_from: date | None,
    date_till: date | None,
    granularity: SalesGranularity,
) -> list[SalesStatisticsBucket]:
    if date_from is None or date_till is None:
        return bucket_rows

    rows_by_period = {
        bucket.period_start: bucket
        for bucket in bucket_rows
        if bucket.period_start is not None
    }
    filled: list[SalesStatisticsBucket] = []
    for period_start in _generate_period_starts(date_from, date_till, granularity):
        existing = rows_by_period.get(period_start)
        if existing is not None:
            filled.append(existing)
        else:
            filled.append(
                _build_bucket(
                    period_start=period_start,
                    units_sold=0,
                    revenue=Decimal("0"),
                    order_count=0,
                )
            )
    return filled


def _sales_metrics_columns() -> tuple:
    return (
        func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
        func.coalesce(func.sum(OrderItem.line_total), 0).label("revenue"),
        func.count(func.distinct(Order.id)).label("order_count"),
    )


async def _query_sales_totals(
    db: AsyncSession,
    conditions: list[ColumnElement[bool]],
) -> SalesStatisticsTotals:
    units_sold_col, revenue_col, order_count_col = _sales_metrics_columns()
    totals_row = (
        await db.execute(
            select(units_sold_col, revenue_col, order_count_col)
            .select_from(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Car, Car.id == OrderItem.car_id)
            .where(*conditions)
        )
    ).one()
    return _build_totals(
        int(totals_row.units_sold),
        Decimal(str(totals_row.revenue)),
        int(totals_row.order_count),
    )


async def _query_time_buckets(
    db: AsyncSession,
    conditions: list[ColumnElement[bool]],
    granularity: SalesGranularity,
) -> list[SalesStatisticsBucket]:
    period_start = func.date_trunc(granularity.value, Order.completed_at).label(
        "period_start"
    )
    units_sold_col, revenue_col, order_count_col = _sales_metrics_columns()
    bucket_rows = (
        await db.execute(
            select(period_start, units_sold_col, revenue_col, order_count_col)
            .select_from(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Car, Car.id == OrderItem.car_id)
            .where(*conditions)
            .group_by(period_start)
            .order_by(period_start)
        )
    ).all()
    return [
        _build_bucket(
            period_start=_truncate_to_period(row.period_start, granularity),
            units_sold=int(row.units_sold),
            revenue=Decimal(str(row.revenue)),
            order_count=int(row.order_count),
        )
        for row in bucket_rows
    ]


async def _query_group_buckets(
    db: AsyncSession,
    conditions: list[ColumnElement[bool]],
    group_by: SalesGroupBy,
) -> list[SalesStatisticsBucket]:
    units_sold_col, revenue_col, order_count_col = _sales_metrics_columns()

    if group_by == SalesGroupBy.BRAND:
        group_id_col = Car.brand_id.label("group_id")
        group_key_col = func.max(OrderItem.brand_name).label("group_key")
        group_by_cols = (Car.brand_id,)
    elif group_by == SalesGroupBy.MODEL:
        group_id_col = Car.model_id.label("group_id")
        group_key_col = func.max(OrderItem.model_name).label("group_key")
        group_by_cols = (Car.model_id,)
    elif group_by == SalesGroupBy.SELLER:
        group_id_col = Car.seller_id.label("group_id")
        group_key_col = func.max(User.email).label("group_key")
        group_by_cols = (Car.seller_id,)
    else:
        group_key_col = Car.body_type.label("group_key")
        group_by_cols = (Car.body_type,)
        query = (
            select(group_key_col, units_sold_col, revenue_col, order_count_col)
            .select_from(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Car, Car.id == OrderItem.car_id)
        )
        bucket_rows = (
            await db.execute(
                query.where(*conditions)
                .group_by(*group_by_cols)
                .order_by(revenue_col.desc())
            )
        ).all()
        return [
            _build_bucket(
                group_key=str(row.group_key),
                units_sold=int(row.units_sold),
                revenue=Decimal(str(row.revenue)),
                order_count=int(row.order_count),
            )
            for row in bucket_rows
        ]

    query = (
        select(group_id_col, group_key_col, units_sold_col, revenue_col, order_count_col)
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Car, Car.id == OrderItem.car_id)
    )
    if group_by == SalesGroupBy.SELLER:
        query = query.join(User, User.id == Car.seller_id)

    bucket_rows = (
        await db.execute(
            query.where(*conditions)
            .group_by(*group_by_cols)
            .order_by(revenue_col.desc())
        )
    ).all()

    return [
        _build_bucket(
            group_id=row.group_id,
            group_key=str(row.group_key),
            units_sold=int(row.units_sold),
            revenue=Decimal(str(row.revenue)),
            order_count=int(row.order_count),
        )
        for row in bucket_rows
    ]


async def get_sales_statistics(
    db: AsyncSession,
    user: User,
    *,
    granularity: SalesGranularity | None = None,
    group_by: SalesGroupBy | None = None,
    brand_id: UUID | None = None,
    model_id: UUID | None = None,
    seller_id: UUID | None = None,
    date_from: date | None = None,
    date_till: date | None = None,
) -> SalesStatisticsResponse:
    if group_by is None and granularity is None:
        raise BadRequest("granularity is required when group_by is not set")

    await _validate_filters(
        db,
        brand_id=brand_id,
        model_id=model_id,
        date_from=date_from,
        date_till=date_till,
    )

    conditions, effective_seller_id = _build_sales_filter_conditions(
        user,
        brand_id=brand_id,
        model_id=model_id,
        seller_id=seller_id,
        date_from=date_from,
        date_till=date_till,
    )

    totals = await _query_sales_totals(db, conditions)

    if group_by is not None:
        buckets = await _query_group_buckets(db, conditions, group_by)
    else:
        assert granularity is not None
        buckets = await _query_time_buckets(db, conditions, granularity)
        buckets = _zero_fill_buckets(
            buckets,
            date_from=date_from,
            date_till=date_till,
            granularity=granularity,
        )

    return SalesStatisticsResponse(
        granularity=granularity if group_by is None else None,
        group_by=group_by,
        filters=SalesStatisticsFilters(
            brand_id=brand_id,
            model_id=model_id,
            seller_id=effective_seller_id,
            date_from=date_from,
            date_till=date_till,
            group_by=group_by,
        ),
        buckets=buckets,
        totals=totals,
    )


async def get_order_statistics(
    db: AsyncSession,
    user: User,
    *,
    seller_id: UUID | None = None,
    date_from: date | None = None,
    date_till: date | None = None,
) -> OrderStatisticsResponse:
    if date_from is not None and date_till is not None and date_from > date_till:
        raise BadRequest("date_from must be on or before date_till")

    conditions, effective_seller_id = _build_order_scope_conditions(
        user,
        seller_id=seller_id,
        date_from=date_from,
        date_till=date_till,
    )

    status_query = (
        select(Order.status, func.count(func.distinct(Order.id)).label("count"))
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Car, Car.id == OrderItem.car_id)
    )
    if conditions:
        status_query = status_query.where(*conditions)
    status_query = status_query.group_by(Order.status)

    status_rows = (await db.execute(status_query)).all()
    counts_by_status = {row.status: int(row.count) for row in status_rows}

    pending = counts_by_status.get(OrderStatus.PENDING, 0)
    confirmed = counts_by_status.get(OrderStatus.CONFIRMED, 0)
    cancelled = counts_by_status.get(OrderStatus.CANCELLED, 0)
    completed = counts_by_status.get(OrderStatus.COMPLETED, 0)

    funnel_total = pending + confirmed + cancelled + completed
    non_cancelled = pending + confirmed + completed

    cancellation_rate = (
        _quantize_money(Decimal(cancelled) / Decimal(funnel_total))
        if funnel_total > 0
        else None
    )
    completion_rate = (
        _quantize_money(Decimal(completed) / Decimal(non_cancelled))
        if non_cancelled > 0
        else None
    )

    pipeline_conditions = [
        *conditions,
        Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED]),
    ]
    scoped_order_ids = (
        select(Order.id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Car, Car.id == OrderItem.car_id)
        .where(*pipeline_conditions)
        .distinct()
        .scalar_subquery()
    )
    pipeline_value = await db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.id.in_(scoped_order_ids)
        )
    )

    return OrderStatisticsResponse(
        filters=OrderStatisticsFilters(
            seller_id=effective_seller_id,
            date_from=date_from,
            date_till=date_till,
        ),
        orders_by_status=[
            OrderStatusCount(status=status.value, count=counts_by_status.get(status, 0))
            for status in OrderStatus
        ],
        cancellation_rate=cancellation_rate,
        completion_rate=completion_rate,
        pending_pipeline_value=_quantize_money(Decimal(str(pipeline_value or 0))),
    )


def _build_inventory_scope(
    user: User,
    *,
    seller_id: UUID | None,
) -> tuple[list[ColumnElement[bool]], UUID | None]:
    if _is_admin(user):
        effective_seller_id = seller_id
        conditions: list[ColumnElement[bool]] = []
        if seller_id is not None:
            conditions.append(Car.seller_id == seller_id)
        return conditions, effective_seller_id

    return [Car.seller_id == user.id], user.id


async def get_inventory_statistics(
    db: AsyncSession,
    user: User,
    *,
    seller_id: UUID | None = None,
) -> InventoryStatisticsResponse:
    conditions, effective_seller_id = _build_inventory_scope(user, seller_id=seller_id)

    active_listings = await db.scalar(
        select(func.count())
        .select_from(Car)
        .where(*(conditions + [Car.status == CarStatus.PUBLISHED]))
    )
    sold_inventory = await db.scalar(
        select(func.count())
        .select_from(Car)
        .where(*(conditions + [Car.status == CarStatus.SOLD]))
    )
    avg_price = await db.scalar(
        select(func.avg(Car.price))
        .select_from(Car)
        .where(*(conditions + [Car.status == CarStatus.PUBLISHED]))
    )

    brand_rows = (
        await db.execute(
            select(Car.brand_id, func.count().label("count"))
            .select_from(Car)
            .where(*(conditions + [Car.status == CarStatus.PUBLISHED]))
            .group_by(Car.brand_id)
            .order_by(func.count().desc())
        )
    ).all()

    return InventoryStatisticsResponse(
        filters=InventoryStatisticsFilters(seller_id=effective_seller_id),
        active_listings=int(active_listings or 0),
        sold_inventory=int(sold_inventory or 0),
        avg_listing_price=(
            _quantize_money(Decimal(str(avg_price))) if avg_price is not None else None
        ),
        by_brand=[
            InventoryBrandBreakdown(brand_id=row.brand_id, count=int(row.count))
            for row in brand_rows
        ],
    )
