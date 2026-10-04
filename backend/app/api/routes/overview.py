from fastapi import APIRouter

from app.api.deps import Service
from app.schemas import Envelope, OverviewData

router = APIRouter()


@router.get("/overview", response_model=Envelope[OverviewData])
def overview(service: Service):
    return {"meta": service.meta, "data": service.overview()}
