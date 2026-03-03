import uvicorn
import logging
from app.core.logging_config import setup_logging


def run_dev():
    setup_logging(logging.DEBUG)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9333,
        reload=True,
        log_level="debug",
        reload_excludes=["_*", "*.log", "data/*"],
        reload_dirs=["app"],
    )


def run_prod():
    setup_logging(logging.INFO)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9333,
        reload=False,
        log_level="info",
    )
