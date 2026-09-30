from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import Summary
from app.services.summary_service import SummaryService


class FakeLLM:
    def generate_text(self, prompt: str) -> str:
        assert "OCR TEXT:" in prompt
        return "Ringkasan dokumen transaksi." 


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

    assert isinstance(summary, Summary)
    assert "Ringkasan" in summary.summary_text
