from fastapi import APIRouter

from app.api.v1.endpoints import auth, catalog, connections, dashboard, health, ingestion, orgs

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(orgs.router)
api_router.include_router(dashboard.router)
api_router.include_router(ingestion.router)
api_router.include_router(catalog.router)
api_router.include_router(connections.router)
