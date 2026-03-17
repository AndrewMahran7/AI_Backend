"""Async background worker that polls for pending jobs and processes them."""

import asyncio
import logging
import time
from collections import deque

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.providers.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.repositories.job import JobRepository
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

# How long to sleep (seconds) when there are no pending jobs.
_POLL_INTERVAL: float = 2.0

# Exception message substrings that indicate an upstream rate-limit response.
_RATE_LIMIT_SIGNALS = ("429", "quota", "rate limit", "resource_exhausted", "too many requests")


class RateLimiter:
    """Sliding-window rate limiter with exponential back-off.

    Tracks job completions over a 60-second window and enforces a
    maximum jobs-per-minute cap.  When an upstream rate-limit error is
    detected the limiter enters exponential back-off, doubling the wait
    on each consecutive failure up to ``backoff_max``.

    Parameters
    ----------
    rpm:
        Maximum jobs per minute.  Pass ``0`` to disable the cap.
    min_delay:
        Minimum pause inserted between every job regardless of the
        window utilisation.
    backoff_initial:
        Starting back-off duration in seconds on the first rate-limit hit.
    backoff_max:
        Upper bound for the exponential back-off.
    """

    _WINDOW: float = 60.0  # sliding-window width in seconds

    def __init__(
        self,
        rpm: int,
        min_delay: float,
        backoff_initial: float,
        backoff_max: float,
    ) -> None:
        self._rpm = rpm
        self._min_delay = min_delay
        self._backoff_initial = backoff_initial
        self._backoff_max = backoff_max

        self._window: deque[float] = deque()  # timestamps of recent job starts
        self._backoff_current: float = backoff_initial
        self._in_backoff: bool = False

    # ── Public interface ──────────────────────────────────────────────────

    async def acquire(self) -> None:
        """Block until it is safe to start the next job."""
        # Enforce minimum inter-job delay first.
        if self._min_delay > 0:
            await asyncio.sleep(self._min_delay)

        if self._rpm <= 0:
            return  # rate limiting disabled

        while True:
            now = time.monotonic()
            # Drop timestamps outside the sliding window.
            while self._window and self._window[0] <= now - self._WINDOW:
                self._window.popleft()

            if len(self._window) < self._rpm:
                self._window.append(now)
                return

            # Window is full — calculate how long until the oldest slot frees.
            wait = self._WINDOW - (now - self._window[0])
            logger.info(
                "Rate limit: %d/%d jobs in last %.0fs — waiting %.1fs",
                len(self._window),
                self._rpm,
                self._WINDOW,
                wait,
            )
            await asyncio.sleep(max(wait, 0.1))

    def notify_success(self) -> None:
        """Reset back-off counters after a successful job."""
        if self._in_backoff:
            logger.info("Rate limiter: back-off cleared after successful job.")
        self._in_backoff = False
        self._backoff_current = self._backoff_initial

    async def notify_rate_limited(self) -> None:
        """Apply exponential back-off after a rate-limit error."""
        self._in_backoff = True
        wait = min(self._backoff_current, self._backoff_max)
        logger.warning(
            "Rate limit error from upstream — backing off for %.1fs "
            "(next back-off cap: %.1fs)",
            wait,
            min(self._backoff_current * 2, self._backoff_max),
        )
        await asyncio.sleep(wait)
        self._backoff_current = min(self._backoff_current * 2, self._backoff_max)


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Return True when *exc* looks like an upstream rate-limit response."""
    msg = str(exc).lower()
    return any(signal in msg for signal in _RATE_LIMIT_SIGNALS)


async def run_worker() -> None:
    """Run the job worker loop indefinitely.

    The worker:
    1. Opens a new DB session per iteration.
    2. Uses ``SELECT … FOR UPDATE SKIP LOCKED`` to claim one pending job.
    3. Acquires a rate-limiter slot before dispatching.
    4. Dispatches the job to the appropriate handler.
    5. Applies exponential back-off on upstream rate-limit errors.
    6. Sleeps briefly when idle.
    """
    settings = get_settings()

    if not settings.gemini_configured:
        logger.warning(
            "Gemini API key is not configured. "
            "The worker will poll but cannot process jobs until a key is set."
        )

    limiter = RateLimiter(
        rpm=settings.effective_rpm,
        min_delay=settings.effective_min_job_delay,
        backoff_initial=settings.WORKER_BACKOFF_INITIAL,
        backoff_max=settings.WORKER_BACKOFF_MAX,
    )

    logger.info(
        "Job worker started (poll=%.1fs, rpm=%d, min_delay=%.1fs, tier=%s)",
        _POLL_INTERVAL,
        settings.effective_rpm,
        settings.effective_min_job_delay,
        settings.GEMINI_TIER,
    )

    while True:
        try:
            async with AsyncSessionLocal() as session:
                job_repo = JobRepository(session)
                job = await job_repo.get_next_pending_job()

                if job is None:
                    await asyncio.sleep(_POLL_INTERVAL)
                    continue

                logger.info("Picked up job %s (type=%s)", job.id, job.job_type)

                # Acquire a rate-limiter slot before hitting the Gemini API.
                await limiter.acquire()

                if job.job_type == "PROCESS_RECORD":
                    llm = GeminiLLMProvider()
                    embeddings = GeminiEmbeddingProvider()
                    service = IngestionService(
                        session=session,
                        llm=llm,
                        embeddings=embeddings,
                    )
                    try:
                        await service.process_record_job(job.id)
                        limiter.notify_success()
                    except Exception as exc:
                        if _is_rate_limit_error(exc):
                            # Re-queue by resetting the job to pending so it is
                            # retried after back-off, rather than marking failed.
                            await job_repo.update_job_status(job.id, "pending")
                            await session.commit()
                            await limiter.notify_rate_limited()
                        else:
                            raise
                else:
                    logger.warning("Unknown job type: %s – marking failed", job.job_type)
                    await job_repo.mark_failed(job.id, f"Unknown job type: {job.job_type}")
                    await session.commit()
                    limiter.notify_success()

        except Exception:
            logger.exception("Unhandled error in worker loop")
            await asyncio.sleep(_POLL_INTERVAL)
