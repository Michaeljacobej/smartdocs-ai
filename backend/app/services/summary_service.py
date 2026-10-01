import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document, Summary
from app.prompts.summary import get_summary_prompt_template
from app.services.llm.base import LLMProvider


class SummaryService:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider
        self.settings = get_settings()

    def generate_for_document(self, db: Session, document: Document) -> Summary:
        if not document.ocr_result or not document.ocr_result.raw_text:
            raise ValueError("OCR result not available for this document")

        existing = document.summary
        if existing and self.settings.summary_reuse_existing and existing.summary_text:
            return existing

        raw_text = document.ocr_result.raw_text
        max_chars = self.settings.summary_max_ocr_chars
        if len(raw_text) > max_chars:
            raw_text = raw_text[:max_chars]

        template = get_summary_prompt_template(getattr(document, "document_type", None))
        prompt = template.format(raw_ocr_text=raw_text)
        summary_text = self._generate_summary_text(prompt, document, raw_text)

        if existing:
            existing.summary_text = summary_text
            db.add(existing)
            db.flush()
            db.refresh(existing)
            return existing

        summary = Summary(
            document_id=document.id,
            summary_text=summary_text,
        )
        db.add(summary)
        db.flush()
        db.refresh(summary)
        return summary

    def _generate_summary_text(self, prompt: str, document: Document, raw_text: str) -> str:
        try:
            if hasattr(self.llm_provider, "generate_summary_text"):
                candidate = self.llm_provider.generate_summary_text(prompt).strip()
            else:
                candidate = self.llm_provider.generate_text(prompt).strip()

            if candidate:
                return candidate
        except Exception:
            pass

        return self._fallback_summary(document=document, raw_text=raw_text)

    def _fallback_summary(self, document: Document, raw_text: str) -> str:
        document_type = getattr(document, "document_type", None)
        if document_type:
            resolved_type = str(document_type).strip().lower()
        else:
            resolved_type = self._infer_document_type(raw_text)
        extracted = getattr(document, "extracted_data", None)

        if resolved_type == "invoice":
            if extracted:
                vendor = getattr(extracted, "vendor_corrected", None) or getattr(extracted, "vendor_original", None)
                doc_number = getattr(extracted, "document_number_corrected", None) or getattr(extracted, "document_number_original", None)
                doc_date = getattr(extracted, "document_date_corrected", None) or getattr(extracted, "document_date_original", None)
                total = getattr(extracted, "total_amount_corrected", None) or getattr(extracted, "total_amount_original", None)
                tax_amount = getattr(extracted, "tax_amount_corrected", None) or getattr(extracted, "tax_amount_original", None)
                currency = getattr(extracted, "currency_corrected", None) or getattr(extracted, "currency_original", None)

                sentences: list[str] = []
                vendor_text = vendor or "informasi tidak tersedia"
                if doc_number:
                    sentences.append(f"Dokumen ini merupakan invoice {doc_number} untuk {vendor_text}.")
                else:
                    sentences.append(f"Dokumen ini merupakan invoice yang diterbitkan untuk {vendor_text}.")
                if doc_date:
                    sentences.append(f"Transaksi terjadi pada tanggal {self._format_display_date(doc_date)}.")
                if total is not None:
                    total_text = str(int(total)) if float(total).is_integer() else str(total)
                    currency_name = currency or "IDR"
                    sentences.append(f"Total nilai transaksi adalah {currency_name} {total_text}.")
                if tax_amount is not None:
                    tax_text = str(int(tax_amount)) if float(tax_amount).is_integer() else str(tax_amount)
                    sentences.append(f"Pajak yang tercatat adalah {tax_text}.")
                sentences.append("Informasi ini penting untuk review tagihan dan proses penagihan pelanggan.")
                summary = " ".join(sentences).strip()
                return summary if summary.endswith(".") else summary + "."

            parsed = self._parse_invoice_summary(raw_text)
            if parsed:
                return parsed

        elif resolved_type == "receipt":
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            summary = (
                "Dokumen ini merupakan struk pembayaran yang berisi rincian transaksi utama untuk kebutuhan verifikasi."
                " Informasi yang terlihat mencakup tanggal transaksi, nominal pembayaran, dan rincian item atau layanan yang dibeli."
            )
            if lines:
                first = lines[0][:180]
                summary += f" Konten awal yang terbaca menunjukkan: {first}."
            return summary

        elif resolved_type == "billing_statement":
            summary = (
                "Dokumen ini merupakan laporan tagihan atau statement yang berisi informasi saldo dan kewajiban pembayaran."
                " Informasi utama yang terlihat mencakup periode tagihan, nominal yang harus dibayarkan, dan detail rekening atau akun terkait."
            )
            if raw_text:
                summary += " Informasi lebih lanjut dapat dikonfirmasi melalui dokumen sumber bila diperlukan."
            return summary

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        summary = "Dokumen ini merupakan dokumen bisnis yang memuat informasi utama untuk kebutuhan review operasional."
        if lines:
            first = lines[0][:180]
            summary += f" Konten awal yang terbaca menunjukkan: {first}."
        summary += " Informasi yang tidak tersedia pada dokumen dicatat sebagai informasi tidak tersedia."
        return summary

    @staticmethod
    def _infer_document_type(raw_text: str) -> str:
        upper = raw_text.upper()
        if any(token in upper for token in ["INVOICE", "FAKTUR", "INV-", "INV "]):
            return "invoice"
        if any(token in upper for token in ["RECEIPT", "STRUK", "NOTA"]):
            return "receipt"
        if any(token in upper for token in ["BILLING STATEMENT", "STATEMENT"]):
            return "billing_statement"
        return "other"

    @staticmethod
    def _format_display_date(raw_value: str | None) -> str:
        if not raw_value:
            return "informasi tidak tersedia"
        cleaned = raw_value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                parsed = datetime.strptime(cleaned, fmt)
                months = {
                    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
                    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember",
                }
                return f"{parsed.day:02d} {months[parsed.month]} {parsed.year}"
            except ValueError:
                continue
        return cleaned

    def _parse_invoice_summary(self, raw_text: str) -> str | None:
        text = raw_text.strip()
        if not text:
            return None

        lower_text = text.lower()
        if not any(keyword in lower_text for keyword in ["invoice", "pelanggan", "jatuh tempo", "sub total", "total:"]):
            return None

        invoice_number = self._extract_first_match(text, r"(?:invoice\s*#?\s*|invoice\s*)([A-Za-z0-9\-]+)")
        customer = self._extract_customer_name(text)
        issue_date = self._extract_date(text, [r"tanggal\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", r"date\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"])
        due_date = self._extract_date(text, [r"jatuh\s+tempo\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", r"due\s*date\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"])
        subtotal = self._extract_money(text, r"sub\s*total\s*[:\-]?\s*rp\s*([0-9.]+)", r"subtotal\s*[:\-]?\s*rp\s*([0-9.]+)")
        total = self._extract_money(text, r"total\s*[:\-]?\s*rp\s*([0-9.]+)", r"grand\s*total\s*[:\-]?\s*rp\s*([0-9.]+)")
        bank_name = self._extract_bank_name(text)
        account = self._extract_first_match(text, r"(?:rekening|account)\s*(?:bank)?\s*[:\-]?\s*([A-Za-z0-9\s/\-]+)")
        swift = self._extract_first_match(text, r"(?:swift|bic)\s*[:\-]?\s*([A-Za-z0-9]+)")

        sentences: list[str] = []
        if invoice_number:
            sentences.append(f"Dokumen ini merupakan invoice #{invoice_number} dengan tanggal transaksi {self._format_display_date(issue_date) if issue_date else 'informasi tidak tersedia'}.")
        else:
            sentences.append(f"Dokumen ini merupakan invoice yang diterbitkan pada tanggal {self._format_display_date(issue_date) if issue_date else 'informasi tidak tersedia'}.")

        if customer:
            sentences.append(f"Dokumen ini ditujukan untuk {customer}.")
        elif issue_date:
            sentences.append("Dokumen ini mencakup transaksi pelanggan dengan informasi alamat yang perlu dikonfirmasi lebih lanjut.")

        if due_date:
            sentences.append(f"Tagihan ini jatuh tempo pada {self._format_display_date(due_date)}.")

        if subtotal:
            sentences.append(f"Subtotal transaksi tercatat sebesar Rp {subtotal}.")
        if total:
            sentences.append(f"Total nilai transaksi adalah Rp {total}.")

        if bank_name or account or swift:
            bank_text = bank_name or "informasi bank tidak tersedia"
            account_text = account or "informasi rekening tidak tersedia"
            swift_text = swift or "informasi SWIFT/BIC tidak tersedia"
            sentences.append(f"Pembayaran dapat dilakukan melalui {bank_text} dengan rekening {account_text}, serta kode SWIFT/BIC {swift_text}.")

        if not sentences:
            return None

        final_summary = " ".join(sentences)
        final_summary = re.sub(r"\s+", " ", final_summary).strip()
        return final_summary if final_summary.endswith(".") else final_summary + "."

    def _extract_first_match(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            return None
        return match.group(1).strip()

    def _extract_customer_name(self, text: str) -> str | None:
        customer = self._extract_first_match(text, r"(?:pelanggan|customer)\s*[:\-]?\s*([A-Za-z0-9&/().,\- ]{2,120})")
        if customer:
            return customer

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if "pelanggan" in line.lower() or "customer" in line.lower():
                if idx + 1 < len(lines):
                    candidate = lines[idx + 1].strip()
                    if 2 <= len(candidate) <= 120:
                        return candidate
        return None

    def _extract_address(self, text: str) -> str:
        address = self._extract_first_match(text, r"(?:alamat|address)\s*[:\-]?\s*([A-Za-z0-9,./\-\s]{4,200})")
        if address:
            return address

        for line in text.splitlines():
            l = line.strip()
            if "alamat" in l.lower() or "address" in l.lower():
                continue
            if len(l) > 4 and any(ch.isalpha() for ch in l):
                return l
        return "informasi alamat tidak tersedia"

    def _extract_date(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            value = self._extract_first_match(text, pattern)
            if value:
                return value
        return None

    def _extract_money(self, text: str, *patterns: str) -> str | None:
        for pattern in patterns:
            value = self._extract_first_match(text, pattern)
            if value:
                cleaned = value.replace(".", "").replace(",", "")
                if cleaned.isdigit():
                    return f"{int(cleaned):,}".replace(",", ".")
        return None

    def _extract_bank_name(self, text: str) -> str | None:
        bank = self._extract_first_match(text, r"(?:nama\s+bank|bank\s*name)\s*[:\-]?\s*([A-Za-z0-9\s&./\-]{2,80})")
        if bank:
            return bank
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if line.lower().startswith("nama bank") or line.lower().startswith("bank"):
                return line.split(":", 1)[-1].strip() if ":" in line else line
        return None


