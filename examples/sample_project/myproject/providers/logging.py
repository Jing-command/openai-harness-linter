"""Logging provider.

Provider that can be imported by service, runtime, and ui layers.
"""

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class StructuredLogger:
    """Structured logging wrapper."""

    def __init__(self, name: str) -> None:
        """Initialize logger."""
        self._logger = logging.getLogger(name)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(message, extra=kwargs)
