import logging
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging_config import setup_logging, get_logger
from app.core.config import settings

setup_logging(logging.DEBUG)
logger = get_logger(__name__)

# Suppress noisy debug output from multipart parser
import logging as _logging
_logging.getLogger("python_multipart").setLevel(_logging.WARNING)

logger.info(f"APP_NAME={settings.APP_NAME}")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    openapi_tags=[
        {"name": "Workers", "description": "Worker registration and heartbeat"},
        {"name": "Datasets", "description": "Dataset submission and download"},
        {"name": "Jobs", "description": "Training job management"},
        {"name": "Models", "description": "Trained model approval and download"},
    ]
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.1f}ms")
    return response


# API routes
from app.api import routes_workers, routes_datasets, routes_jobs, routes_models, routes_dashboard

app.include_router(routes_workers.router, prefix="/api/workers", tags=["Workers"])
app.include_router(routes_datasets.router, prefix="/api/datasets", tags=["Datasets"])
app.include_router(routes_jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(routes_models.router, prefix="/api/models", tags=["Models"])
app.include_router(routes_dashboard.router, tags=["Dashboard"])


@app.on_event("startup")
def startup_event():
    logger.info("Starting nnUNet Dashboard...")
    from app.core.database import init_db
    init_db()
    logger.info("Database ready.")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
