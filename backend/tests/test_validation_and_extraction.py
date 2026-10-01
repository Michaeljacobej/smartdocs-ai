import pytest
from pydantic import ValidationError

from app.schemas.extraction import ExtractedFields
from app.services.extraction_service import ExtractionService


def test_extraction_schema_validation_invalid_date() -> None:
    with pytest.raises(ValidationError):
        ExtractedFields(document_date="09-30-2026")


def test_extraction_confidence_payload_is_json_serializable() -> None:
    service = ExtractionService()

    extracted, confidence_payload = service.extract(
        "INVOICE INV-2026-001\nABC Medical Supply\n2026-10-01\nTOTAL 12500000\nTAX 500000\nIDR"
    )

    assert extracted.document_number == "2026-001"
    assert isinstance(confidence_payload["rule_matches"], dict)
