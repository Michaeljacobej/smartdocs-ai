from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}


class FileValidationError(ValueError):
    pass


def validate_upload_file(file: UploadFile, size: int, settings: Settings) -> None:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise FileValidationError("Unsupported file extension")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise FileValidationError("Unsupported file MIME type")

    if size > settings.max_file_size_bytes:
        raise FileValidationError(
            f"File exceeds max size of {settings.max_file_size_mb} MB"
        )
