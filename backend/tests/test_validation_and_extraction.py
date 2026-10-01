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


def test_extracted_fields_accept_total_alias() -> None:
    payload = {
        "document_number": "INV-001",
        "vendor": "ABC Medical",
        "document_date": "2026-10-01",
        "total": "12500000",
        "tax_amount": "500000",
        "currency": "idr",
    }

    extracted = ExtractedFields.model_validate(payload)

    assert extracted.total_amount == 12500000
    assert extracted.tax_amount == 500000
    assert extracted.currency == "IDR"


def test_rule_extraction_reads_total_with_rp_prefix() -> None:
    service = ExtractionService()
    text = """
    Invoice # 71
    Produk saya 2 1.250.000 2.500.000
    Layanan saya 1 2.500.000 2.500.000
    Sub total: Rp 5.000.000
    Total: Rp 5.000.000
    """

    extracted, _ = service.extract(text)

    assert extracted.total_amount == 5000000
