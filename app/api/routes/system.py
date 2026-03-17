"""System information route."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.system import SystemInfoResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get(
    "/info",
    response_model=SystemInfoResponse,
    summary="System info",
    description="Returns non-secret runtime metadata about the running service.",
)
async def system_info(settings: Settings = Depends(get_settings)) -> SystemInfoResponse:
    """Expose safe runtime information for diagnostics."""
    return SystemInfoResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENV,
        debug=settings.DEBUG,
        api_prefix=settings.API_PREFIX,
        database_configured=settings.database_configured,
        gemini_configured=settings.gemini_configured,
    )
