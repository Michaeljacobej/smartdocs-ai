import re

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document, Summary
from app.prompts.summary import SUMMARY_PROMPT_TEMPLATE
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

        prompt = SUMMARY_PROMPT_TEMPLATE.format(raw_ocr_text=raw_text)
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
        extracted = getattr(document, "extracted_data", None)
        doc_type = getattr(document, "document_type", None) or "dokumen transaksi"

        if extracted:
            vendor = extracted.vendor_corrected or extracted.vendor_original
            doc_number = extracted.document_number_corrected or extracted.document_number_original
            doc_date = extracted.document_date_corrected or extracted.document_date_original
            total = extracted.total_amount_corrected or extracted.total_amount_original
            tax_amount = extracted.tax_amount_corrected or extracted.tax_amount_original
            currency = extracted.currency_corrected or extracted.currency_original

            sentences: list[str] = []
            vendor_text = vendor or "informasi tidak tersedia"
            sentences.append(f"Dokumen ini merupakan {doc_type} yang diterbitkan oleh {vendor_text}.")
            if doc_number:
                sentences.append(f"Nomor dokumen yang tercatat adalah {doc_number}.")
            if doc_date:
                sentences.append(f"Transaksi berlangsung pada tanggal {doc_date}.")
            if total is not None:
                total_text = f"{total:,.2f}".rstrip("0").rstrip(".")
                if currency:
                    sentences.append(f"Total nilai transaksi tercatat sebesar {currency} {total_text}.")
                else:
                    sentences.append(f"Total nilai transaksi tercatat sebesar {total_text}.")
            if tax_amount is not None:
                tax_text = f"{tax_amount:,.2f}".rstrip("0").rstrip(".")
                sentences.append(f"Besaran pajak atau potongan yang tersedia adalah {tax_text}.")
            if not sentences:
                sentences.append("Dokumen ini merupakan dokumen transaksi dengan informasi utama yang belum lengkap untuk review.")
            else:
                sentences.append("Informasi ini disusun untuk kebutuhan review operasional dan dapat dikonfirmasi kembali bila terdapat data pendukung yang belum lengkap.")
            summary = " ".join(sentences).strip()
            if not summary.endswith("."):
                summary += "."
            return summary

        parsed = self._parse_invoice_summary(raw_text)
        if parsed:
            return parsed

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        summary = "Dokumen ini merupakan dokumen transaksi yang memuat informasi utama untuk kebutuhan review bisnis."
        if lines:
            first = lines[0][:180]
            summary += f" Konten awal yang terbaca menunjukkan: {first}."
        summary += " Informasi lebih lanjut dapat dikonfirmasi melalui dokumen sumber bila diperlukan."
        return summary

    def _parse_invoice_summary(self, raw_text: str) -> str | None:
        text = raw_text.strip()
        if not text:
            return None

        lower_text = text.lower()
        if not any(keyword in lower_text for keyword in ["invoice", "pelanggan", "jatuh tempo", "sub total", "total:"]):
            return None

        invoice_number = self._extract_first_match(text, r"(?:invoice\s*#?|invoice\s*)(\d+[A-Za-z0-9\-]*)")
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
            sentences.append(f"Invoice #{invoice_number} diterbitkan pada tanggal {self._format_date(issue_date) if issue_date else 'informasi tidak tersedia'}.")
        else:
            sentences.append(f"Dokumen ini merupakan invoice yang diterbitkan pada tanggal {self._format_date(issue_date) if issue_date else 'informasi tidak tersedia'}.")

        if customer:
            sentences.append(f"Dokumen ini ditujukan untuk {customer} yang beralamat di {self._extract_address(text)}.")
        elif issue_date:
            sentences.append("Dokumen ini mencakup transaksi pelanggan dengan informasi alamat yang perlu dikonfirmasi lebih lanjut.")

        if due_date:
            sentences.append(f"Tagihan ini jatuh tempo pada {self._format_date(due_date)}, sehingga masuk dalam periode pembayaran yang sudah ditentukan.")

        if subtotal:
            sentences.append(f"Subtotal transaksi tercatat sebesar Rp {subtotal}.")
        if total:
            sentences.append(f"Total tagihan yang tercantum pada invoice adalah Rp {total}, sesuai dengan jumlah yang harus dibayarkan oleh pelanggan.")

        if bank_name or account or swift:
            bank_text = bank_name or "informasi bank tidak tersedia"
            account_text = account or "informasi rekening tidak tersedia"
            swift_text = swift or "informasi SWIFT/BIC tidak tersedia"
            sentences.append(f"Pembayaran dapat dilakukan melalui {bank_text} dengan rekening {account_text}, serta kode SWIFT/BIC {swift_text} untuk kebutuhan transfer internasional.")

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
        patterns = [
            r"(?:nama\s+bank|bank\s+name)\s*[:\-]?\s*([A-Za-z0-9 &/.-]{2,80})",
            r"(?:bank)\s*[:\-]?\s*([A-Za-z0-9 &/.-]{2,80})",
        ]
        for pattern in patterns:
            value = self._extract_first_match(text, pattern)
            if value:
                return value
        return None

    def _format_date(self, raw_date: str | None) -> str:
        if not raw_date:
            return "informasi tidak tersedia"
        try:
            match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", raw_date)
            if not match:
                return raw_date
            day, month, year = match.groups()
            year_int = int(year)
            if year_int < 100:
                year_int += 2000 if year_int < 50 else 1900
            return f"{day.zfill(2)} {self._month_name(int(month))} {year_int}"
        except Exception:
            return raw_date

    def _month_name(self, month_number: int) -> str:
        months = {
            1: "Januari",
            2: "Februari",
            3: "Maret",
            4: "April",
            5: "Mei",
            6: "Juni",
            7: "Juli",
            8: "Agustus",
            9: "September",
            10: "Oktober",
            11: "November",
            12: "Desember",
        }
        return months.get(month_number, str(month_number))

