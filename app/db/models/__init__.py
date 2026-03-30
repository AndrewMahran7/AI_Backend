"""Database models package.

Import all model modules here so that ``Base.metadata`` is populated
before Alembic inspects it.
"""

from app.db.models.record import Record  # noqa: F401
from app.db.models.chunk import RecordChunk  # noqa: F401
from app.db.models.summary import RecordSummary  # noqa: F401
from app.db.models.job import Job  # noqa: F401
from app.db.models.query_log import QueryLog  # noqa: F401
from app.db.models.conversation import Conversation  # noqa: F401
from app.db.models.message import Message  # noqa: F401

__all__ = ["Record", "RecordChunk", "RecordSummary", "Job", "QueryLog"]
