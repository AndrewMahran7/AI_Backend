"""FastAPI lifespan handler – startup & shutdown hooks."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the application lifecycle.

    * **Startup** – configure logging, validate settings, launch worker.
    * **Shutdown** – cancel worker, emit clean-shutdown log.
    """
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info("Starting %s v%s [env=%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENV)
    logger.info("Debug mode: %s", settings.DEBUG)
    logger.info("API prefix: %s", settings.API_PREFIX)
    logger.info("Database configured: %s", settings.database_configured)
    logger.info("Gemini configured: %s", settings.gemini_configured)

    # Launch the background job worker.
    from app.jobs.worker import run_worker  # noqa: E402

    worker_task = asyncio.create_task(run_worker(), name="job-worker")
    logger.info("Background job worker launched.")
    logger.info("Application startup complete.")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Job worker stopped.")
    logger.info("Application shutdown complete.")
