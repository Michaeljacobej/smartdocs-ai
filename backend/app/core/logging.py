import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from logging import LogRecord

_LOG_CONTEXT: ContextVar[dict[str, object]] = ContextVar("log_context", default={})


class JsonFormatter(logging.Formatter):
    _RESERVED_FIELDS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record: LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        context = _LOG_CONTEXT.get()
        if context:
            payload.update(context)

        if hasattr(record, "event"):
            payload["event"] = getattr(record, "event")

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._RESERVED_FIELDS and not key.startswith("_")
        }
        if extra_fields:
            payload.update(extra_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def bind_log_context(**kwargs: object) -> None:
    current = dict(_LOG_CONTEXT.get())
    current.update({k: v for k, v in kwargs.items() if v is not None})
    _LOG_CONTEXT.set(current)


def clear_log_context() -> None:
    _LOG_CONTEXT.set({})


def configure_logging(log_level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level.upper())

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(log_level.upper())
        logger.propagate = False
