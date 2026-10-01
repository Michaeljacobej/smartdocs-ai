import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

from app.core.config import get_settings


@dataclass
class OCRLine:
    text: str
    confidence: float | None


@dataclass
class OCRServiceResult:
    raw_text: str
    lines: list[OCRLine]
    processing_time_ms: int


class OCRService:
    def __init__(self) -> None:
        self._ocr_engine = None
        self.settings = get_settings()

    def _engine(self):
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as exc:
                raise RuntimeError("PaddleOCR is not installed") from exc
            self._ocr_engine = PaddleOCR(use_angle_cls=True, lang="en")
        return self._ocr_engine

    def _ocr_image(self, image_np: np.ndarray) -> list[OCRLine]:
        result = self._engine().ocr(image_np, cls=True)
        lines: list[OCRLine] = []
        for page in result or []:
            for item in page or []:
                text = item[1][0] if item and item[1] else ""
                confidence = float(item[1][1]) if item and item[1] else None
                if text:
                    lines.append(OCRLine(text=text, confidence=confidence))
        return lines

    def _searchable_pdf_text(self, doc: fitz.Document) -> str:
        pages: list[str] = []
        for page in doc:
            text = page.get_text("text", sort=True).strip()
            if text:
                pages.append(text)
        return "\n".join(pages)

    def _ocr_pdf_page(self, page: fitz.Page) -> list[OCRLine]:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_np = np.array(image)
        return self._ocr_image(image_np)

    def _ocr_pages(self, doc: fitz.Document, page_indexes: list[int]) -> list[OCRLine]:
        max_workers = min(2, max(1, len(page_indexes)))
        lines: list[OCRLine] = []
        if not page_indexes:
            return lines

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(lambda page_index: self._ocr_pdf_page(doc.load_page(page_index)), page_indexes))
            for page_lines in results:
                lines.extend(page_lines)
        return lines

    def extract_text(self, file_path: Path) -> OCRServiceResult:
        start = time.perf_counter()
        suffix = file_path.suffix.lower()
        lines: list[OCRLine] = []

        if suffix == ".pdf":
            doc = fitz.open(file_path)
            try:
                searchable_text = self._searchable_pdf_text(doc)
                if searchable_text and len(searchable_text) >= self.settings.ocr_searchable_text_threshold:
                    raw_text = searchable_text
                    elapsed = int((time.perf_counter() - start) * 1000)
                    return OCRServiceResult(raw_text=raw_text, lines=[OCRLine(text=searchable_text, confidence=None)], processing_time_ms=elapsed)

                total_pages = doc.page_count
                pages_to_ocr = min(total_pages, self.settings.ocr_max_pages)
                page_indexes = list(range(pages_to_ocr))
                lines = self._ocr_pages(doc, page_indexes)
            finally:
                doc.close()
        else:
            image = Image.open(file_path).convert("RGB")
            image_np = np.array(image)
            lines.extend(self._ocr_image(image_np))

        raw_text = "\n".join(line.text for line in lines)
        elapsed = int((time.perf_counter() - start) * 1000)
        return OCRServiceResult(raw_text=raw_text, lines=lines, processing_time_ms=elapsed)
