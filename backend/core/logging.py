"""Structured logging via structlog. JSON in prod, pretty-print in dev."""
import logging, sys
import structlog
from core.settings import settings

def setup_logging() -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,

        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if settings.is_production:
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.APP_DEBUG else logging.INFO
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    )
    for noisy in ("httpx", "httpcore", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)
