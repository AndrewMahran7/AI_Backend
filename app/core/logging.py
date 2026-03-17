"""Structured logging configuration for the application."""

import logging
import sys
from typing import Optional


def setup_logging(log_level: Optional[str] = None) -> None:
    """Configure the root logger with a clean, readable format.

    Parameters
    ----------
    log_level:
        The minimum log level (e.g. ``"DEBUG"``, ``"INFO"``).  Falls back to
        ``INFO`` when *None*.
    """
    level = getattr(logging, (log_level or "INFO").upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls (e.g. during tests).
    if not root_logger.handlers:
        root_logger.addHandler(handler)

    # Silence overly chatty third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
