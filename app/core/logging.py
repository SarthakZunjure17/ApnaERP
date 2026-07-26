import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    """
    Configures structured logging for the application.
    Sets standard output formatting with level, timestamp, and logger name.
    """
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s:%(lineno)d) - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "level": settings.LOG_LEVEL.upper(),
            },
        },
        "root": {
            "level": settings.LOG_LEVEL.upper(),
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "app": {"handlers": ["console"], "level": settings.LOG_LEVEL.upper(), "propagate": False},
        },
    }

    import logging.config
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger("app")
    logger.info(f"Logging initialized with level: {settings.LOG_LEVEL}")
