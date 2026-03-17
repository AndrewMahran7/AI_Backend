"""Repository for :class:`Job` lifecycle operations."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import Job


class JobRepository:
    """Data-access layer for the ``jobs`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(
        self,
        job_type: str,
        payload: dict[str, Any] | None = None,
    ) -> Job:
        """Insert a new job with status ``pending``."""
        job = Job(
            job_type=job_type,
            payload=payload or {},
            status="pending",
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get_job_by_id(self, job_id: uuid.UUID) -> Job | None:
        """Return a job by primary key, or ``None`` if not found."""
        stmt = select(Job).where(Job.id == job_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_pending_job(self, job_type: str | None = None) -> Job | None:
        """Return the oldest pending job, optionally filtered by type.

        Uses ``FOR UPDATE SKIP LOCKED`` so that concurrent workers do not
        pick up the same job.
        """
        stmt = (
            select(Job)
            .where(Job.status == "pending")
            .order_by(Job.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job_type is not None:
            stmt = stmt.where(Job.job_type == job_type)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: uuid.UUID,
        status: str,
    ) -> None:
        """Transition a job to a new status with appropriate timestamps."""
        values: dict[str, Any] = {"status": status}
        now = datetime.now(timezone.utc)

        if status == "running":
            values["started_at"] = now
        elif status in ("completed", "failed"):
            values["completed_at"] = now

        stmt = update(Job).where(Job.id == job_id).values(**values)
        await self._session.execute(stmt)

    async def mark_failed(
        self,
        job_id: uuid.UUID,
        error: str,
    ) -> None:
        """Mark a job as failed and record the error message."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(
                status="failed",
                error=error,
                completed_at=now,
            )
        )
        await self._session.execute(stmt)
