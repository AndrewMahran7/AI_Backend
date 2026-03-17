"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.lifecycle import lifespan

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS middleware ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ───────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_PREFIX)


# ── Root endpoint ────────────────────────────────────────────────────────
@app.get("/")
async def root() -> dict[str, str]:
    """Return basic service identity and status."""
    return {
        "name": settings.APP_NAME,
        "status": "running",
        "environment": settings.ENV,
    }
