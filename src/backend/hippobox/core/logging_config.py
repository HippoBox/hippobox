import logging
import logging.config
import os
from pathlib import Path


class PrefixFilter(logging.Filter):
    COLOR = "\x1b[34m"
    RESET = "\x1b[0m"

    def filter(self, record: logging.LogRecord) -> bool:
        record.prefix_name = f"{self.COLOR}[{record.name.upper()}]{self.RESET}"
        return True


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "hippobox.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "add_prefix": {
            "()": "hippobox.core.logging_config.PrefixFilter",
        },
    },
    "formatters": {
        "uvicorn_prefix": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(prefix_name)s %(message)s",
            "use_colors": True,
        },
        "detail_prefix": {
            "format": "[%(asctime)s] [%(levelname)s] %(prefix_name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "uvicorn_prefix",
            "filters": ["add_prefix"],
            "level": LOG_LEVEL,
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "detail_prefix",
            "filters": ["add_prefix"],
            "filename": str(LOG_FILE),
            "encoding": "utf-8",
            "level": "DEBUG",
        },
    },
    "loggers": {
        "database": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "qdrant": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "embedding": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "hippobox": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "knowledge": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}


def setup_logger():
    logging.config.dictConfig(LOGGING_CONFIG)
