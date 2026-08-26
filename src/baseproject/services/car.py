from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from baseproject.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from baseproject.models.car import Car
from baseproject.models.car_enums import CarStatus
from baseproject.models.car_photo import CarPhoto
from baseproject.models.user import User, UserRole
from baseproject.schemas.car import (
    CarCreateRequest,
    CarDetailPublic,
    CarListResponse,
    CarPhotoCreateRequest,
    CarPhotoPublic,
    CarPublic,
    CarUpdateRequest,
)
from baseproject.services import car_catalog as catalog_service


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _can_manage_car(user: User, car: Car) -> bool:
    return _is_admin(user) or car.seller_id == user.id


def _require_seller_or_admin(user: User) -> None:
    if user.role not in (UserRole.SELLER, UserRole.ADMIN):
        raise Forbidden("Seller or admin role required")


def _car_to_public(car: Car) -> CarPublic:
    return CarPublic.model_validate(car)


async def _get_car_or_404(db: AsyncSession, car_id: UUID) -> Car:
    car = await db.get(Car, car_id)
    if car is None:
        raise NotFound("Car not found")
    return car


async def _load_photos(db: AsyncSession, car_id: UUID) -> list[CarPhoto]:
    return (
        await db.scalars(
            select(CarPhoto)
            .where(CarPhoto.car_id == car_id)
            .order_by(CarPhoto.sort_order, CarPhoto.id)
        )
    ).all()


def _build_list_query(
    *,
    brand_id: UUID | None,
    model_id: UUID | None,
    min_price,
    max_price,
    min_year: int | None,
    max_year: int | None,
    max_mileage: int | None,
    body_type: str | None,
    engine_type: str | None,
    transmission: str | None,
    drive: str | None,
    status: CarStatus | None,
    seller_id: UUID | None,
):
    query = select(Car)
    if status is not None:
        query = query.where(Car.status == status)
    if seller_id is not None:
        query = query.where(Car.seller_id == seller_id)
    if brand_id is not None:
        query = query.where(Car.brand_id == brand_id)
    if model_id is not None:
        query = query.where(Car.model_id == model_id)
    if min_price is not None:
        query = query.where(Car.price >= min_price)
    if max_price is not None:
        query = query.where(Car.price <= max_price)
    if min_year is not None:
        query = query.where(Car.year >= min_year)
    if max_year is not None:
        query = query.where(Car.year <= max_year)
    if max_mileage is not None:
        query = query.where(Car.mileage <= max_mileage)
    if body_type is not None:
        query = query.where(Car.body_type == body_type)
    if engine_type is not None:
        query = query.where(Car.engine_type == engine_type)
    if transmission is not None:
        query = query.where(Car.transmission == transmission)
    if drive is not None:
        query = query.where(Car.drive == drive)
    return query


async def list_cars(
    db: AsyncSession,
    *,
    brand_id: UUID | None = None,
    model_id: UUID | None = None,
    min_price=None,
    max_price=None,
    min_year: int | None = None,
    max_year: int | None = None,
    max_mileage: int | None = None,
    body_type: str | None = None,
    engine_type: str | None = None,
    transmission: str | None = None,
    drive: str | None = None,
    status: CarStatus | None = CarStatus.PUBLISHED,
    seller_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> CarListResponse:
    base_query = _build_list_query(
        brand_id=brand_id,
        model_id=model_id,
        min_price=min_price,
        max_price=max_price,
        min_year=min_year,
        max_year=max_year,
        max_mileage=max_mileage,
        body_type=body_type,
        engine_type=engine_type,
        transmission=transmission,
        drive=drive,
        status=status,
        seller_id=seller_id,
    )
    total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    cars = (
        await db.scalars(
            base_query.order_by(Car.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()
    return CarListResponse(
        items=[_car_to_public(car) for car in cars],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


async def get_car(
    db: AsyncSession,
    car_id: UUID,
    *,
    user: User | None = None,
) -> CarDetailPublic:
    car = await _get_car_or_404(db, car_id)
    if car.status != CarStatus.PUBLISHED:
        if user is None or not _can_manage_car(user, car):
            raise NotFound("Car not found")
    photos = await _load_photos(db, car_id)
    return CarDetailPublic(
        **_car_to_public(car).model_dump(),
        photos=[CarPhotoPublic.model_validate(photo) for photo in photos],
    )


async def get_car_for_owner(
    db: AsyncSession,
    car_id: UUID,
    user: User,
) -> CarDetailPublic:
    return await get_car(db, car_id, user=user)


async def create_car(
    db: AsyncSession,
    user: User,
    data: CarCreateRequest,
) -> CarPublic:
    _require_seller_or_admin(user)
    await catalog_service.get_brand(db, data.brand_id)
    await catalog_service.validate_brand_model_pair(db, data.brand_id, data.model_id)

    if (
        data.status not in (CarStatus.DRAFT, CarStatus.PUBLISHED)
        and user.role != UserRole.ADMIN
    ):
        raise BadRequest("Only draft or published status allowed on create")

    car = Car(
        seller_id=user.id,
        brand_id=data.brand_id,
        model_id=data.model_id,
        year=data.year,
        mileage=data.mileage,
        vin=data.vin,
        body_type=data.body_type,
        engine_type=data.engine_type,
        engine_size=data.engine_size,
        drive=data.drive,
        transmission=data.transmission,
        color=data.color,
        price=data.price,
        warranty_months=data.warranty_months,
        description=data.description,
        status=data.status,
    )
    db.add(car)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise Conflict("Car with this VIN already exists") from exc
    return _car_to_public(car)


async def update_car(
    db: AsyncSession,
    car_id: UUID,
    user: User,
    data: CarUpdateRequest,
) -> CarPublic:
    car = await _get_car_or_404(db, car_id)
    if not _can_manage_car(user, car):
        raise Forbidden("Not allowed to update this car")

    updates = data.model_dump(exclude_unset=True)
    brand_id = updates.get("brand_id", car.brand_id)
    model_id = updates.get("model_id", car.model_id)

    if "brand_id" in updates or "model_id" in updates:
        await catalog_service.get_brand(db, brand_id)
        await catalog_service.validate_brand_model_pair(db, brand_id, model_id)

    if "status" in updates:
        new_status = updates["status"]
        allowed_statuses = (
            CarStatus.DRAFT,
            CarStatus.PUBLISHED,
            CarStatus.SOLD,
            CarStatus.ARCHIVED,
        )
        if new_status not in allowed_statuses:
            raise BadRequest("Invalid status")
        if (
            new_status in (CarStatus.SOLD, CarStatus.ARCHIVED)
            and user.role != UserRole.ADMIN
            and car.seller_id != user.id
        ):
            raise Forbidden("Not allowed to update this car")

    for field, value in updates.items():
        setattr(car, field, value)
    car.updated_at = datetime.now(UTC)

    try:
        await db.flush()
    except IntegrityError as exc:
        raise Conflict("Car with this VIN already exists") from exc
    return _car_to_public(car)


async def delete_car(db: AsyncSession, car_id: UUID, user: User) -> None:
    car = await _get_car_or_404(db, car_id)
    if not _can_manage_car(user, car):
        raise Forbidden("Not allowed to delete this car")
    await db.delete(car)


async def add_photo(
    db: AsyncSession,
    car_id: UUID,
    user: User,
    data: CarPhotoCreateRequest,
) -> CarPhotoPublic:
    car = await _get_car_or_404(db, car_id)
    if not _can_manage_car(user, car):
        raise Forbidden("Not allowed to update this car")

    if data.is_primary:
        existing_photos = await _load_photos(db, car_id)
        for photo in existing_photos:
            photo.is_primary = False

    photo = CarPhoto(
        car_id=car_id,
        url=data.url,
        sort_order=data.sort_order,
        is_primary=data.is_primary,
    )
    db.add(photo)
    await db.flush()
    car.updated_at = datetime.now(UTC)
    return CarPhotoPublic.model_validate(photo)


async def delete_photo(
    db: AsyncSession,
    car_id: UUID,
    photo_id: UUID,
    user: User,
) -> None:
    car = await _get_car_or_404(db, car_id)
    if not _can_manage_car(user, car):
        raise Forbidden("Not allowed to update this car")

    photo = await db.get(CarPhoto, photo_id)
    if photo is None or photo.car_id != car_id:
        raise NotFound("Photo not found")

    await db.delete(photo)
    car.updated_at = datetime.now(UTC)
