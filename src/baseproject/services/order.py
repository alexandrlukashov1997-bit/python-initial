from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from baseproject.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from baseproject.models.car import Car
from baseproject.models.car_enums import CarStatus
from baseproject.models.order import Order
from baseproject.models.order_enums import OrderStatus
from baseproject.models.order_item import OrderItem
from baseproject.models.user import User, UserRole
from baseproject.schemas.order import (
    OrderCreateRequest,
    OrderDetailPublic,
    OrderItemPublic,
    OrderListResponse,
    OrderPublic,
)
from baseproject.services import car_catalog as catalog_service

_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.COMPLETED: set(),
}

_ORDER_NUMBER_ATTEMPTS = 8


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _generate_order_number() -> str:
    return uuid4().hex[:12]


async def _allocate_order_number(db: AsyncSession) -> str:
    for _ in range(_ORDER_NUMBER_ATTEMPTS):
        number = _generate_order_number()
        exists = await db.scalar(
            select(Order.id).where(Order.order_number == number)
        )
        if exists is None:
            return number
    raise Conflict("Could not allocate unique order number")


async def _load_items(db: AsyncSession, order_id: UUID) -> list[OrderItem]:
    return (
        await db.scalars(
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.id)
        )
    ).all()


def _order_to_public(order: Order) -> OrderPublic:
    return OrderPublic.model_validate(order)


def _order_to_detail(order: Order, items: list[OrderItem]) -> OrderDetailPublic:
    return OrderDetailPublic(
        **_order_to_public(order).model_dump(),
        items=[OrderItemPublic.model_validate(item) for item in items],
    )


async def _get_order_or_404(db: AsyncSession, order_id: UUID) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise NotFound("Order not found")
    return order


async def _seller_owns_any_item(db: AsyncSession, order_id: UUID, seller_id: UUID) -> bool:
    result = await db.scalar(
        select(func.count())
        .select_from(OrderItem)
        .join(Car, Car.id == OrderItem.car_id)
        .where(OrderItem.order_id == order_id, Car.seller_id == seller_id)
    )
    return bool(result)


async def _assert_can_view(
    db: AsyncSession,
    order: Order,
    user: User | None,
) -> None:
    if user is None:
        raise Forbidden("Authentication required")
    if _is_admin(user):
        return
    if order.user_id is not None and order.user_id == user.id:
        return
    if user.role == UserRole.SELLER and await _seller_owns_any_item(
        db, order.id, user.id
    ):
        return
    raise Forbidden("Insufficient permissions")


async def _assert_can_update_status(db: AsyncSession, order: Order, user: User) -> None:
    if _is_admin(user):
        return
    if user.role == UserRole.SELLER and await _seller_owns_any_item(
        db, order.id, user.id
    ):
        return
    raise Forbidden("Seller or admin role required")


async def _mark_cars_sold(db: AsyncSession, items: list[OrderItem]) -> None:
    seen: set[UUID] = set()
    for item in items:
        if item.car_id in seen:
            continue
        seen.add(item.car_id)
        car = await db.get(Car, item.car_id)
        if car is None:
            raise NotFound("Car not found")
        if car.status == CarStatus.SOLD:
            raise Conflict(f"Car {item.car_id} is already sold")
        if car.status != CarStatus.PUBLISHED:
            raise Conflict(f"Car {item.car_id} is not available for sale")
        car.status = CarStatus.SOLD


async def _revert_cars_published(db: AsyncSession, items: list[OrderItem]) -> None:
    seen: set[UUID] = set()
    for item in items:
        if item.car_id in seen:
            continue
        seen.add(item.car_id)
        car = await db.get(Car, item.car_id)
        if car is not None and car.status == CarStatus.SOLD:
            car.status = CarStatus.PUBLISHED


async def create_order(
    db: AsyncSession,
    data: OrderCreateRequest,
    user: User | None,
) -> OrderDetailPublic:
    built_items: list[OrderItem] = []
    total = Decimal("0.00")

    for line in data.items:
        car = await db.get(Car, line.car_id)
        if car is None:
            raise NotFound(f"Car {line.car_id} not found")
        if car.status != CarStatus.PUBLISHED:
            raise BadRequest(f"Car {line.car_id} is not available for order")

        brand = await catalog_service.get_brand(db, car.brand_id)
        model = await catalog_service.get_model(db, car.model_id)
        line_total = (car.price * line.quantity).quantize(Decimal("0.01"))
        total += line_total
        built_items.append(
            OrderItem(
                car_id=car.id,
                brand_name=brand.name,
                model_name=model.name,
                body_type=car.body_type,
                unit_price=car.price,
                quantity=line.quantity,
                line_total=line_total,
            )
        )

    order = Order(
        order_number=await _allocate_order_number(db),
        user_id=user.id if user is not None else None,
        customer_first_name=data.customer_first_name.strip(),
        customer_last_name=data.customer_last_name.strip(),
        customer_email=str(data.customer_email).lower(),
        customer_phone=data.customer_phone.strip(),
        additional_info=data.additional_info,
        warranty=data.warranty,
        status=OrderStatus.PENDING,
        total_amount=total.quantize(Decimal("0.01")),
    )
    db.add(order)
    await db.flush()

    for item in built_items:
        item.order_id = order.id
        db.add(item)
    await db.flush()

    items = await _load_items(db, order.id)
    return _order_to_detail(order, items)


async def get_order(
    db: AsyncSession,
    order_id: UUID,
    user: User | None,
) -> OrderDetailPublic:
    order = await _get_order_or_404(db, order_id)
    await _assert_can_view(db, order, user)
    items = await _load_items(db, order.id)
    return _order_to_detail(order, items)


async def get_order_by_number(
    db: AsyncSession,
    order_number: str,
) -> OrderDetailPublic:
    order = await db.scalar(
        select(Order).where(Order.order_number == order_number)
    )
    if order is None:
        raise NotFound("Order not found")
    # Guest checkout: short order_number is the capability token
    items = await _load_items(db, order.id)
    return _order_to_detail(order, items)


async def list_orders(
    db: AsyncSession,
    user: User,
    *,
    status: OrderStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> OrderListResponse:
    query = select(Order)

    if _is_admin(user):
        pass
    elif user.role == UserRole.SELLER:
        query = (
            query.join(OrderItem, OrderItem.order_id == Order.id)
            .join(Car, Car.id == OrderItem.car_id)
            .where(Car.seller_id == user.id)
            .distinct()
        )
    else:
        query = query.where(Order.user_id == user.id)

    if status is not None:
        query = query.where(Order.status == status)

    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = await db.scalar(count_query) or 0

    orders = (
        await db.scalars(
            query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()

    return OrderListResponse(
        items=[_order_to_public(order) for order in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


async def update_order_status(
    db: AsyncSession,
    order_id: UUID,
    new_status: OrderStatus,
    user: User,
) -> OrderDetailPublic:
    order = await _get_order_or_404(db, order_id)
    await _assert_can_update_status(db, order, user)

    current = order.status
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise BadRequest(
            f"Cannot transition from {current.value} to {new_status.value}"
        )

    items = await _load_items(db, order.id)

    if new_status == OrderStatus.CONFIRMED:
        await _mark_cars_sold(db, items)
    elif new_status == OrderStatus.CANCELLED and current == OrderStatus.CONFIRMED:
        await _revert_cars_published(db, items)

    order.status = new_status
    await db.flush()
    items = await _load_items(db, order.id)
    return _order_to_detail(order, items)
