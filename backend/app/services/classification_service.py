import re

from app.prompts.classification import CLASSIFICATION_RULE_HINT
from app.services.llm.base import LLMProvider

ALLOWED_TYPES = {"invoice", "receipt", "billing_statement", "other"}


class ClassificationService:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

    @staticmethod
    def _normalize_label(value: str) -> str | None:
        normalized = re.sub(r"[^a-z_\s]", "", value.lower()).strip()
        normalized = normalized.replace(" ", "_")
        if normalized in ALLOWED_TYPES:
            return normalized
        if normalized == "billingstatement":
            return "billing_statement"
        if normalized == "payment_receipt":
            return "receipt"
        return None

    def classify(self, ocr_text: str) -> str:
        text = ocr_text.upper()
        if re.search(r"\bINVOICE\b", text):
            return "invoice"
        if re.search(r"\bRECEIPT\b", text):
            return "receipt"
        if re.search(r"BILLING\s+STATEMENT", text):
            return "billing_statement"

        if self.llm_provider:
            prompt = f"{CLASSIFICATION_RULE_HINT}\n\nOCR TEXT:\n{ocr_text}"
            try:
                candidate = self.llm_provider.generate_text(prompt).strip()
                normalized = self._normalize_label(candidate)
                if normalized:
                    return normalized
            except Exception:
                pass

        return "other"
