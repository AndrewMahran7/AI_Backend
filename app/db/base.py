"""SQLAlchemy declarative base and metadata for all ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class.

    All ORM models must inherit from this class so that Alembic can
    discover them via ``Base.metadata``.
    """

    pass


def import_all_models() -> None:
    """Force-import every model module so metadata is fully populated.

    Call this before Alembic autogenerate or any operation that relies on
    ``Base.metadata`` being complete.
    """
    import app.db.models  # noqa: F401
