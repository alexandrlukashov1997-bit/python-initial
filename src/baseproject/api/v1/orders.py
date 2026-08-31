from uuid import UUID

from fastapi import APIRouter, Query, status

from baseproject.api.deps import CurrentUser, DbSession, OptionalCurrentUser
from baseproject.models.order_enums import OrderStatus
from baseproject.schemas.order import (
    OrderCreateRequest,
    OrderDetailPublic,
    OrderListResponse,
    OrderStatusUpdateRequest,
)
from baseproject.services import order as order_service

router = APIRouter()


@router.post("", response_model=OrderDetailPublic, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreateRequest,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
) -> OrderDetailPublic:
    return await order_service.create_order(db, payload, current_user)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> OrderListResponse:
    return await order_service.list_orders(
        db,
        current_user,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get("/by-number/{order_number}", response_model=OrderDetailPublic)
async def get_order_by_number(
    order_number: str,
    db: DbSession,
) -> OrderDetailPublic:
    return await order_service.get_order_by_number(db, order_number)


@router.get("/{order_id}", response_model=OrderDetailPublic)
async def get_order(
    order_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> OrderDetailPublic:
    return await order_service.get_order(db, order_id, current_user)


@router.patch("/{order_id}/status", response_model=OrderDetailPublic)
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> OrderDetailPublic:
    return await order_service.update_order_status(
        db,
        order_id,
        payload.status,
        current_user,
    )
