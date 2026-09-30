import re

from app.prompts.classification import CLASSIFICATION_RULE_HINT
from app.services.llm.base import LLMProvider

ALLOWED_TYPES = {"invoice", "receipt", "billing_statement", "other"}


class ClassificationService:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

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
                candidate = self.llm_provider.generate_text(prompt).strip().lower()
                if candidate in ALLOWED_TYPES:
                    return candidate
            except Exception:
                pass

        return "other"
