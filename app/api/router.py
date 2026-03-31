"""Central API router that aggregates all route modules."""

from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.dentrix import router as dentrix_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.sap import router as sap_router
from app.api.routes.sources import router as sources_router
from app.api.routes.system import router as system_router
from app.api.routes.tools import router as tools_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(conversations_router)
api_router.include_router(ingest_router)
api_router.include_router(sources_router)
api_router.include_router(system_router)
api_router.include_router(sap_router)
api_router.include_router(dentrix_router)
api_router.include_router(tools_router)
