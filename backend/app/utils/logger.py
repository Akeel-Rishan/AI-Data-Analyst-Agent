"""Reusable application logging configuration."""

import logging

from app.config import settings


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a consistently configured logger without duplicate handlers."""
    configured_logger = logging.getLogger(name)
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    configured_logger.setLevel(level)

    if not configured_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        configured_logger.addHandler(handler)

    configured_logger.propagate = False
    return configured_logger


logger = get_logger("app")
