from uuid import UUID

from fastapi import APIRouter, status

from baseproject.api.deps import CurrentAdmin, DbSession
from baseproject.schemas.car_brand import (
    CarBrandCreateRequest,
    CarBrandPublic,
    CarModelCreateRequest,
    CarModelPublic,
)
from baseproject.services import car_catalog as catalog_service

router = APIRouter()


@router.get("", response_model=list[CarBrandPublic])
async def list_brands(db: DbSession) -> list[CarBrandPublic]:
    return await catalog_service.list_brands(db)


@router.post(
    "",
    response_model=CarBrandPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_brand(
    body: CarBrandCreateRequest,
    db: DbSession,
    _admin: CurrentAdmin,
) -> CarBrandPublic:
    return await catalog_service.create_brand(db, body)


@router.post(
    "/models",
    response_model=CarModelPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_model(
    body: CarModelCreateRequest,
    db: DbSession,
    _admin: CurrentAdmin,
) -> CarModelPublic:
    return await catalog_service.create_model(db, body)


@router.get("/{brand_id}/models", response_model=list[CarModelPublic])
async def list_models(
    brand_id: UUID,
    db: DbSession,
) -> list[CarModelPublic]:
    return await catalog_service.list_models_for_brand(db, brand_id)
