"""
Structured logging infrastructure.

Provides JSON-formatted logs with correlation IDs and context.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

# Context variable for user ID
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if cid is None:
        cid = str(uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(cid)


def set_user_context(user_id: str) -> None:
    """Set the user ID for the current context."""
    user_id_var.set(user_id)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in a consistent JSON format suitable for log aggregation
    systems like ELK, Datadog, or CloudWatch.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
            "user_id": user_id_var.get(),
        }

        # Add location information
        if record.pathname:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__
            and k
            not in (
                "message",
                "asctime",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "msg",
                "args",
            )
        }
        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str)


class StructuredLogger:
    """
    Structured logger wrapper with context support.

    Provides a convenient interface for logging with automatic context
    injection (correlation ID, user ID, etc.).

    Example:
        logger = StructuredLogger("app.auth")
        logger.info("User logged in", user_id="123", ip="192.168.1.1")
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _log(
        self, level: int, message: str, exc_info: bool = False, **kwargs: Any
    ) -> None:
        """Internal logging method with context injection."""
        extra = {
            "correlation_id": get_correlation_id(),
            "user_id": user_id_var.get(),
            **kwargs,
        }
        self._logger.log(level, message, exc_info=exc_info, extra=extra)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log an error message."""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log an exception with traceback."""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self._log(logging.CRITICAL, message, **kwargs)


def configure_logging(
    level: str = "INFO",
    json_format: bool = True,
    include_timestamp: bool = True,
) -> None:
    """
    Configure the logging system.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting
        include_timestamp: Whether to include timestamps in non-JSON format
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Set formatter
    if json_format:
        handler.setFormatter(StructuredFormatter())
    else:
        format_str = "%(levelname)s - %(name)s - %(message)s"
        if include_timestamp:
            format_str = "%(asctime)s - " + format_str
        handler.setFormatter(logging.Formatter(format_str))

    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
