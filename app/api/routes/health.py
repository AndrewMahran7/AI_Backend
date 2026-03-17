"""Health-check route."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns a simple status payload indicating the service is alive.",
)
async def health_check() -> HealthResponse:
    """Return ``{"status": "ok"}``."""
    return HealthResponse()
