from sqlalchemy.orm import Session

from app.db.models import Document, Summary
from app.prompts.summary import SUMMARY_PROMPT_TEMPLATE
from app.services.llm.base import LLMProvider


class SummaryService:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def generate_for_document(self, db: Session, document: Document) -> Summary:
        if not document.ocr_result or not document.ocr_result.raw_text:
            raise ValueError("OCR result not available for this document")

        prompt = SUMMARY_PROMPT_TEMPLATE.format(raw_ocr_text=document.ocr_result.raw_text)
        summary_text = self.llm_provider.generate_text(prompt).strip()

        existing = document.summary
        if existing:
            existing.summary_text = summary_text
            db.add(existing)
            db.flush()
            db.refresh(existing)
            return existing

        summary = Summary(document_id=document.id, summary_text=summary_text)
        db.add(summary)
        db.flush()
        db.refresh(summary)
        return summary
