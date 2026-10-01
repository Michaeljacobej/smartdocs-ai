import json
import re
from datetime import datetime

from pydantic import ValidationError

from app.prompts.extraction import EXTRACTION_PROMPT_TEMPLATE
from app.schemas.extraction import ExtractedFields
from app.services.llm.base import LLMProvider
from app.utils.amount_parser import parse_amount


class ExtractionError(ValueError):
    pass


class ExtractionService:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

    def extract(self, ocr_text: str, _document_type: str | None = None) -> tuple[ExtractedFields, dict]:
        rule_data = self._rule_extract(ocr_text)
        confidence_payload: dict = {"rule_matches": rule_data.model_dump()}

        needs_llm = any(value is None for value in rule_data.model_dump().values())
        if needs_llm and self.llm_provider:
            try:
                llm_data = self._llm_extract(ocr_text)
                merged = rule_data.model_dump()
                for key, value in llm_data.model_dump().items():
                    if merged.get(key) is None and value is not None:
                        merged[key] = value
                final = ExtractedFields(**merged)
                confidence_payload["llm_used"] = True
                confidence_payload["llm_matches"] = llm_data.model_dump()
                return final, confidence_payload
            except Exception as exc:
                # Keep pipeline running when LLM is unavailable or returns invalid output.
                confidence_payload["llm_used"] = False
                confidence_payload["llm_error"] = str(exc)
                return rule_data, confidence_payload

        confidence_payload["llm_used"] = False
        return rule_data, confidence_payload

    def _rule_extract(self, text: str) -> ExtractedFields:
        doc_number = self._first_match(
            text,
            [
                r"(?<![A-Z0-9])(?:INVOICE|RCPT|BILL)[\s:#-]*([A-Z0-9]+(?:[/-][A-Z0-9]+)*)",
                r"(?<![A-Z0-9])INV(?=\s|#|:|-|/|$)[\s:#-]*([A-Z0-9]+(?:[/-][A-Z0-9]+)*)",
                r"(?<![A-Z0-9])(?:INVOICE|INV|RCPT|BILL)[\s:#-]*([A-Z0-9]+)",
            ],
        )
        if doc_number and doc_number.upper().startswith("OICE"):
            doc_number = None
        if doc_number and doc_number.upper().startswith("INV") and len(doc_number) > 3:
            doc_number = doc_number[3:].lstrip("-/")
        vendor = self._extract_vendor(text)
        doc_date = self._extract_date(text)
        total = self._extract_amount(
            text,
            [
                r"GRAND\s*TOTAL\s*[:\-]?\s*(?:RP|IDR|USD|EUR|SGD|JPY|MYR|THB|PHP)?\s*([0-9][0-9.,\s]*)",
                r"(?<!SUB\s)TOTAL\b\s*(?:AMOUNT)?\s*[:\-]?\s*(?:RP|IDR|USD|EUR|SGD|JPY|MYR|THB|PHP)?\s*([0-9][0-9.,\s]*)",
            ],
        )
        tax = self._extract_amount(
            text,
            [
                r"(?:TAX|PPN|VAT)\s*(?:AMOUNT)?\s*[:\-]?\s*(?:RP|IDR|USD|EUR|SGD|JPY|MYR|THB|PHP)?\s*([0-9][0-9.,\s]*)",
            ],
        )
        currency = self._extract_currency(text)

        return ExtractedFields(
            document_number=doc_number,
            vendor=vendor,
            document_date=doc_date,
            total_amount=total,
            tax_amount=tax,
            currency=currency,
        )

    def _llm_extract(self, text: str) -> ExtractedFields:
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(ocr_text=text)
        raw = self.llm_provider.generate_text(prompt)
        parsed = self._safe_extract_json(raw)
        if parsed is None:
            raise ExtractionError("LLM extraction returned invalid JSON")

        try:
            return ExtractedFields.model_validate(parsed)
        except ValidationError as exc:
            raise ExtractionError("LLM extraction validation failed") from exc

    def _safe_extract_json(self, text: str) -> dict | None:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None

        snippet = match.group(0)
        try:
            data = json.loads(snippet)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return None
        return None

    @staticmethod
    def _first_match(text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                return candidate[:100] if candidate else None
        return None

    @staticmethod
    def _extract_vendor(text: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:8]:
            if any(keyword in line.upper() for keyword in ["INVOICE", "RECEIPT", "BILL"]):
                continue
            if len(line) > 3 and not re.search(r"\d{4}-\d{2}-\d{2}", line):
                return line[:255]
        return None

    @staticmethod
    def _extract_date(text: str) -> str | None:
        patterns = [
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(\d{2}/\d{2}/\d{4})\b",
            r"\b(\d{2}-\d{2}-\d{4})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            raw = match.group(1)
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_amount(text: str, patterns: list[str]) -> float | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return parse_amount(match.group(1))
        return None

    @staticmethod
    def _extract_currency(text: str) -> str | None:
        match = re.search(r"\b(IDR|USD|EUR|SGD|JPY|MYR|THB|PHP|Rp)\b", text, flags=re.IGNORECASE)
        if not match:
            return None
        currency = match.group(1).upper()
        return "IDR" if currency == "RP" else currency
