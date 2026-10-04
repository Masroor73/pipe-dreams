from fastapi import APIRouter

from app.api.routes import assets, audit, governance, health, overview

api_router = APIRouter(prefix="/api")
for _module in (health, overview, assets, audit, governance):
    api_router.include_router(_module.router)
