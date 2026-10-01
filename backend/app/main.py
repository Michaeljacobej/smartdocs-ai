import logging
import os
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.api.errors import AppError, app_error_handler, internal_error_handler
from app.api.routes.documents import requeue_processing_documents_on_startup, router as documents_router
from app.core.config import get_settings
from app.core.logging import bind_log_context, clear_log_context, configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

local_dev_origins = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://0.0.0.0:3001",
    "http://[::1]:3000",
    "http://[::1]:3001",
}

env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
if env_origins:
    local_dev_origins.update(origin.strip() for origin in env_origins.split(",") if origin.strip())

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(local_dev_origins),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, internal_error_handler)


@app.on_event("startup")
def startup_requeue_documents() -> None:
    requeued = requeue_processing_documents_on_startup()
    logger.info(
        "Startup processing queue recovery completed",
        extra={"event": "startup_queue_recovery_completed", "requeued_count": requeued},
    )


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    bind_log_context(request_id=request_id)

    start_time = perf_counter()
    logger.info(
        "HTTP request started",
        extra={
            "event": "http_request_started",
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
        },
    )

    try:
        response = await call_next(request)
        elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "event": "http_request_completed",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
            },
        )
        return response
    except Exception:
        elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
        logger.exception(
            "HTTP request failed",
            extra={
                "event": "http_request_failed",
                "method": request.method,
                "path": request.url.path,
                "duration_ms": elapsed_ms,
            },
        )
        raise
    finally:
        clear_log_context()


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(
        "Request payload validation failed",
        extra={
            "event": "request_validation_failed",
            "method": request.method,
            "path": request.url.path,
            "error_count": len(exc.errors()),
        },
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload",
                "details": exc.errors(),
            }
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
