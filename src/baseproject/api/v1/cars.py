from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, status

from baseproject.api.deps import CurrentUser, DbSession, OptionalCurrentUser
from baseproject.core.exceptions import Forbidden, Unauthorized
from baseproject.models.car_enums import (
    BodyType,
    CarStatus,
    DriveType,
    EngineType,
    TransmissionType,
)
from baseproject.models.user import UserRole
from baseproject.schemas.car import (
    CarCreateRequest,
    CarDetailPublic,
    CarListResponse,
    CarPhotoCreateRequest,
    CarPhotoPublic,
    CarPublic,
    CarUpdateRequest,
)
from baseproject.services import car as car_service

router = APIRouter()


def _resolve_list_scope(
    status: CarStatus | None,
    seller_id: UUID | None,
    current_user: OptionalCurrentUser,
) -> tuple[CarStatus | None, UUID | None]:
    if status == CarStatus.PUBLISHED or status is None:
        return CarStatus.PUBLISHED, seller_id

    if current_user is None:
        raise Unauthorized("Authentication required for non-public listings")

    if current_user.role == UserRole.ADMIN:
        return status, seller_id

    if current_user.role == UserRole.SELLER:
        return status, current_user.id

    raise Forbidden("Insufficient permissions")


@router.get("", response_model=CarListResponse)
async def list_cars(
    db: DbSession,
    brand_id: UUID | None = None,
    model_id: UUID | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    min_year: int | None = Query(default=None, ge=1980),
    max_year: int | None = Query(default=None, ge=1980),
    max_mileage: int | None = Query(default=None, ge=0),
    body_type: BodyType | None = None,
    engine_type: EngineType | None = None,
    transmission: TransmissionType | None = None,
    drive: DriveType | None = None,
    status: CarStatus | None = CarStatus.PUBLISHED,
    seller_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: OptionalCurrentUser = None,
) -> CarListResponse:
    resolved_status, resolved_seller_id = _resolve_list_scope(
        status,
        seller_id,
        current_user,
    )
    return await car_service.list_cars(
        db,
        brand_id=brand_id,
        model_id=model_id,
        min_price=min_price,
        max_price=max_price,
        min_year=min_year,
        max_year=max_year,
        max_mileage=max_mileage,
        body_type=body_type.value if body_type else None,
        engine_type=engine_type.value if engine_type else None,
        transmission=transmission.value if transmission else None,
        drive=drive.value if drive else None,
        status=resolved_status,
        seller_id=resolved_seller_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{car_id}", response_model=CarDetailPublic)
async def get_car(
    car_id: UUID,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
) -> CarDetailPublic:
    return await car_service.get_car(db, car_id, user=current_user)


@router.post("", response_model=CarPublic, status_code=status.HTTP_201_CREATED)
async def create_car(
    body: CarCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> CarPublic:
    return await car_service.create_car(db, current_user, body)


@router.patch("/{car_id}", response_model=CarPublic)
async def update_car(
    car_id: UUID,
    body: CarUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> CarPublic:
    return await car_service.update_car(db, car_id, current_user, body)


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    await car_service.delete_car(db, car_id, current_user)


@router.post(
    "/{car_id}/photos",
    response_model=CarPhotoPublic,
    status_code=status.HTTP_201_CREATED,
)
async def add_photo(
    car_id: UUID,
    body: CarPhotoCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> CarPhotoPublic:
    return await car_service.add_photo(db, car_id, current_user, body)


@router.delete(
    "/{car_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_photo(
    car_id: UUID,
    photo_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    await car_service.delete_photo(db, car_id, photo_id, current_user)
