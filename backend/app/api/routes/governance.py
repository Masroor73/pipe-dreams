from fastapi import APIRouter

from app.api.deps import Service
from app.schemas import DataQualityData, Envelope, EscalationsData, NotCoveredData

router = APIRouter()


@router.get("/escalations", response_model=Envelope[EscalationsData])
def escalations(service: Service):
    return {"meta": service.meta, "data": service.escalations()}


@router.get("/not-covered", response_model=Envelope[NotCoveredData])
def not_covered(service: Service):
    return {"meta": service.meta, "data": service.not_covered()}


@router.get("/data-quality", response_model=Envelope[DataQualityData])
def data_quality(service: Service):
    return {"meta": service.meta, "data": service.data_quality()}
