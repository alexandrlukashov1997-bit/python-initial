from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from baseproject.core.exceptions import BadRequest, Conflict, NotFound
from baseproject.models.car_brand import CarBrand
from baseproject.models.car_model import CarModel
from baseproject.schemas.car_brand import (
    CarBrandCreateRequest,
    CarBrandPublic,
    CarModelCreateRequest,
    CarModelPublic,
)


async def list_brands(db: AsyncSession) -> list[CarBrandPublic]:
    brands = (
        await db.scalars(select(CarBrand).order_by(CarBrand.name))
    ).all()
    return [CarBrandPublic.model_validate(brand) for brand in brands]


async def create_brand(
    db: AsyncSession,
    data: CarBrandCreateRequest,
) -> CarBrandPublic:
    brand = CarBrand(name=data.name.strip())
    db.add(brand)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise Conflict("Brand already exists") from exc
    return CarBrandPublic.model_validate(brand)


async def get_brand(db: AsyncSession, brand_id) -> CarBrand:
    brand = await db.get(CarBrand, brand_id)
    if brand is None:
        raise NotFound("Brand not found")
    return brand


async def list_models_for_brand(
    db: AsyncSession,
    brand_id,
) -> list[CarModelPublic]:
    await get_brand(db, brand_id)
    models = (
        await db.scalars(
            select(CarModel)
            .where(CarModel.brand_id == brand_id)
            .order_by(CarModel.name)
        )
    ).all()
    return [CarModelPublic.model_validate(model) for model in models]


async def create_model(
    db: AsyncSession,
    data: CarModelCreateRequest,
) -> CarModelPublic:
    await get_brand(db, data.brand_id)
    model = CarModel(brand_id=data.brand_id, name=data.name.strip())
    db.add(model)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise Conflict("Model already exists for this brand") from exc
    return CarModelPublic.model_validate(model)


async def get_model(db: AsyncSession, model_id) -> CarModel:
    model = await db.get(CarModel, model_id)
    if model is None:
        raise NotFound("Model not found")
    return model


async def validate_brand_model_pair(
    db: AsyncSession,
    brand_id,
    model_id,
) -> CarModel:
    model = await get_model(db, model_id)
    if model.brand_id != brand_id:
        raise BadRequest("Model does not belong to the selected brand")
    return model
