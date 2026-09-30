from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"
    message = "Bad request"

    def __init__(self, message: str | None = None, code: str | None = None) -> None:
        if message:
            self.message = message
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "DOCUMENT_NOT_FOUND"
    message = "Document not found"


class UnsupportedFileError(AppError):
    status_code = 400
    code = "UNSUPPORTED_FILE"
    message = "Unsupported file"


class SummaryNotReadyError(AppError):
    status_code = 409
    code = "SUMMARY_NOT_READY"
    message = "OCR result not available yet"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "Dependent service unavailable"


class ProcessingFailedError(AppError):
    status_code = 500
    code = "PROCESSING_FAILED"
    message = "Document processing failed"


def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def internal_error_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Unexpected server error"}},
    )
