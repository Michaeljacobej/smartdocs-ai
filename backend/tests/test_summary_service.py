from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.summary_service import SummaryService


class FakeLLM:
    def generate_text(self, prompt: str) -> str:
        assert "OCR TEXT:" in prompt
        return "Ringkasan dokumen transaksi." 


class FailingLLM:
    def generate_text(self, prompt: str) -> str:
        raise RuntimeError("LLM unavailable")


class FakeDB:
    def add(self, _obj):
        return None

    def flush(self):
        return None

    def refresh(self, obj):
        if not getattr(obj, "id", None):
            obj.id = uuid4()
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)


def test_summary_service_generates_from_ocr_text() -> None:
    service = SummaryService(llm_provider=FakeLLM())
    document = SimpleNamespace(
        id=uuid4(),
        ocr_result=SimpleNamespace(raw_text="INVOICE INV-001"),
        summary=None,
    )

    summary = service.generate_for_document(FakeDB(), document)

    assert "Ringkasan" in summary.summary_text


def test_summary_service_reuses_existing_summary() -> None:
    service = SummaryService(llm_provider=FailingLLM())
    from app.db.models import Summary

    existing = Summary(summary_text="Sudah ada")
    document = SimpleNamespace(
        id=uuid4(),
        ocr_result=SimpleNamespace(raw_text="INVOICE INV-001"),
        extracted_data=None,
        summary=existing,
    )

    summary = service.generate_for_document(FakeDB(), document)

    assert summary is existing


def test_summary_service_falls_back_when_llm_fails() -> None:
    service = SummaryService(llm_provider=FailingLLM())
    document = SimpleNamespace(
        id=uuid4(),
        ocr_result=SimpleNamespace(raw_text="INVOICE INV-001\nPT ABC\nTotal Rp 100000"),
        extracted_data=SimpleNamespace(
            document_number_original="INV-001",
            document_number_corrected=None,
            vendor_original="PT ABC",
            vendor_corrected=None,
            document_date_original="2026-10-01",
            document_date_corrected=None,
            total_amount_original=100000,
            total_amount_corrected=None,
            currency_original="IDR",
            currency_corrected=None,
            confidence_data=None,
        ),
        summary=None,
    )

    summary = service.generate_for_document(FakeDB(), document)

    assert "PT ABC" in summary.summary_text
    assert "INV-001" in summary.summary_text
    assert len(summary.summary_text.split()) > 15
    assert "." in summary.summary_text


def test_summary_fallback_is_detailed_when_data_exists() -> None:
    service = SummaryService(llm_provider=FailingLLM())
    document = SimpleNamespace(
        id=uuid4(),
        ocr_result=SimpleNamespace(raw_text="INVOICE INV-001\nPT ABC\nTotal Rp 100000\nTax Rp 10000"),
        extracted_data=SimpleNamespace(
            document_number_original="INV-001",
            document_number_corrected=None,
            vendor_original="PT ABC",
            vendor_corrected=None,
            document_date_original="2026-10-01",
            document_date_corrected=None,
            total_amount_original=100000,
            total_amount_corrected=None,
            tax_amount_original=10000,
            tax_amount_corrected=None,
            currency_original="IDR",
            currency_corrected=None,
            confidence_data=None,
        ),
        summary=None,
    )

    summary = service.generate_for_document(FakeDB(), document)

    assert "PT ABC" in summary.summary_text
    assert "INV-001" in summary.summary_text
    assert "100000" in summary.summary_text
    assert "10.000" in summary.summary_text or "10000" in summary.summary_text
    assert len(summary.summary_text.split()) >= 20


def test_summary_fallback_uses_business_style_writing() -> None:
    service = SummaryService(llm_provider=FailingLLM())
    document = SimpleNamespace(
        id=uuid4(),
        ocr_result=SimpleNamespace(raw_text="INVOICE INV-001\nPT ABC\nTotal Rp 100000\nTax Rp 10000"),
        extracted_data=SimpleNamespace(
            document_number_original="INV-001",
            document_number_corrected=None,
            vendor_original="PT ABC",
            vendor_corrected=None,
            document_date_original="2026-10-01",
            document_date_corrected=None,
            total_amount_original=100000,
            total_amount_corrected=None,
            tax_amount_original=10000,
            tax_amount_corrected=None,
            currency_original="IDR",
            currency_corrected=None,
            confidence_data=None,
        ),
        summary=None,
    )

    summary = service.generate_for_document(FakeDB(), document)

    text = summary.summary_text.lower()
    assert "dokumen ini merupakan" in text
    assert "total nilai transaksi" in text
    assert "pada tanggal" in text


def test_summary_fallback_handles_invoice_style_ocr_text() -> None:
    service = SummaryService(llm_provider=FailingLLM())
    document = SimpleNamespace(
        id=uuid4(),
        ocr_result=SimpleNamespace(
            raw_text=(
                "Pelanggan:\n[Nama perusahaan pelanggan]\n"
                "Tanggal: 08/12/2021\n"
                "Jatuh tempo: 22/12/2021\n"
                "Invoice # 71\n"
                "Produk saya 2 1.250.000 2.500.000\n"
                "Layanan saya 1 2.500.000 2.500.000\n"
                "Sub total: Rp 5.000.000\n"
                "Total: Rp 5.000.000\n"
                "Nama bank\nRekening: 123456789\nSWIFT/BIC: ABCD1234"
            )
        ),
        extracted_data=None,
        summary=None,
    )

    summary = service.generate_for_document(FakeDB(), document)

    text = summary.summary_text.lower()
    assert "invoice #71" in text or "invoice 71" in text
    assert "08 desember 2021" in text or "08" in text
    assert "jatuh tempo" in text
    assert "5.000.000" in text or "5000000" in text
    assert "rekening" in text or "bank" in text
