from datetime import date
from uuid import UUID

from fastapi import APIRouter

from baseproject.api.deps import CurrentSeller, DbSession
from baseproject.schemas.statistics import SalesGranularity, SalesStatisticsResponse
from baseproject.services import statistics as statistics_service

router = APIRouter()


@router.get("/sales", response_model=SalesStatisticsResponse)
async def get_sales_statistics(
    db: DbSession,
    current_user: CurrentSeller,
    granularity: SalesGranularity,
    brand_id: UUID | None = None,
    model_id: UUID | None = None,
    seller_id: UUID | None = None,
    date_from: date | None = None,
    date_till: date | None = None,
) -> SalesStatisticsResponse:
    return await statistics_service.get_sales_statistics(
        db,
        current_user,
        granularity=granularity,
        brand_id=brand_id,
        model_id=model_id,
        seller_id=seller_id,
        date_from=date_from,
        date_till=date_till,
    )
