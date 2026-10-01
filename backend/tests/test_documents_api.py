import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.errors import NotFoundError, UnsupportedFileError
from app.core.config import Settings
from app.main import app
from app.services.service_registry import document_service

client = TestClient(app)


def _doc_stub():
    now = datetime.now(timezone.utc)
    return {
        "id": str(uuid4()),
        "file_name": "invoice.png",
        "mime_type": "image/png",
        "file_size": 1200,
        "document_type": "invoice",
        "processing_status": "PROCESSING",
        "upload_date": now.isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "ocr_result": None,
        "extracted_data": None,
        "summary": None,
    }


def test_upload_path_is_resolved_from_backend_root():
    settings = Settings(upload_dir="./uploads")
    expected = (Path(__file__).resolve().parents[1] / "uploads").resolve()
    assert settings.upload_path == expected


def test_unsupported_file_type(monkeypatch):
    def fake_create(_db, _file, _bytes):
        raise UnsupportedFileError("Unsupported file")

    monkeypatch.setattr(document_service, "create_document", fake_create)
    response = client.post(
        "/documents",
        files={"file": ("script.exe", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE"


def test_document_not_found(monkeypatch):
    def fake_get(_db, _id):
        raise NotFoundError()

    monkeypatch.setattr(document_service, "get_document", fake_get)
    response = client.get(f"/documents/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_basic_document_upload(monkeypatch):
    class Obj:
        def __init__(self):
            for k, v in _doc_stub().items():
                setattr(self, k, v)

    monkeypatch.setattr(document_service, "create_document", lambda _db, _file, _bytes: Obj())
    response = client.post(
        "/documents",
        files={"file": ("invoice.png", b"imgdata", "image/png")},
    )
    assert response.status_code == 201
    assert response.json()["file_name"] == "invoice.png"


def test_upload_returns_quickly_without_waiting_for_background_processing(monkeypatch):
    class Obj:
        def __init__(self):
            for k, v in _doc_stub().items():
                setattr(self, k, v)

    monkeypatch.setattr(document_service, "create_document", lambda _db, _file, _bytes: Obj())

    def slow_process(_db, _id):
        time.sleep(1.5)

    monkeypatch.setattr(document_service, "process_document", slow_process)

    start = time.perf_counter()
    response = client.post(
        "/documents",
        files={"file": ("invoice.png", b"imgdata", "image/png")},
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 201
    assert elapsed < 0.5


def test_corrected_extraction(monkeypatch):
    class Obj:
        def __init__(self):
            payload = _doc_stub()
            payload["processing_status"] = "REVIEWED"
            payload["extracted_data"] = {
                "id": str(uuid4()),
                "document_number_original": "INV-1",
                "document_number_corrected": "INV-0001",
                "vendor_original": "ABC Medicl",
                "vendor_corrected": "ABC Medical",
                "document_date_original": "2026-09-10",
                "document_date_corrected": "2026-09-10",
                "total_amount_original": 1000,
                "total_amount_corrected": 1000,
                "tax_amount_original": 100,
                "tax_amount_corrected": 100,
                "currency_original": "IDR",
                "currency_corrected": "IDR",
                "confidence_data": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            for k, v in payload.items():
                setattr(self, k, v)

    monkeypatch.setattr(document_service, "update_extracted_data", lambda _db, _id, _payload: Obj())
    response = client.put(
        f"/documents/{uuid4()}/extracted-data",
        json={
            "document_number": "INV-0001",
            "vendor": "ABC Medical",
            "document_date": "2026-09-10",
            "total_amount": 1000,
            "tax_amount": 100,
            "currency": "IDR",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["extracted_data"]["vendor_original"] == "ABC Medicl"
    assert body["extracted_data"]["vendor_corrected"] == "ABC Medical"
