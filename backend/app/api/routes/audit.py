from fastapi import APIRouter

from app.api.deps import Service
from app.schemas import AuditData, Envelope

router = APIRouter()


@router.get("/audit", response_model=Envelope[AuditData])
def audit(service: Service):
    return {"meta": service.meta, "data": service.audit()}
