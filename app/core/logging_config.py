import logging
import logging.config
import logging.handlers
import sys
import os

LOG_DIR = "_logs"
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logging(level=logging.DEBUG):
    config = {
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
            }
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
            },
            "file_app": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"{LOG_DIR}/app.log",
                "formatter": "default",
                "encoding": "utf-8",
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 5,
            },
            "file_uvicorn": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"{LOG_DIR}/uvicorn.log",
                "formatter": "default",
                "encoding": "utf-8",
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
            },
        },

        "loggers": {
            "": {  # root logger
                "handlers": ["console", "file_app"],
                "level": level,
            },
            "uvicorn.error": {
                "handlers": ["console", "file_uvicorn"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file_uvicorn"],
                "level": level,
                "propagate": False,
            },
        }
    }

    logging.config.dictConfig(config)


def get_logger(name: str = __name__) -> logging.Logger:
    return logging.getLogger(name)
