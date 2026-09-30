import time
from dataclasses import dataclass
from pathlib import Path

import fitz
import numpy as np
from PIL import Image


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

    def extract_text(self, file_path: Path) -> OCRServiceResult:
        start = time.perf_counter()
        suffix = file_path.suffix.lower()
        lines: list[OCRLine] = []

        if suffix == ".pdf":
            doc = fitz.open(file_path)
            try:
                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    image_np = np.array(image)
                    lines.extend(self._ocr_image(image_np))
            finally:
                doc.close()
        else:
            image = Image.open(file_path).convert("RGB")
            image_np = np.array(image)
            lines.extend(self._ocr_image(image_np))

        raw_text = "\n".join(line.text for line in lines)
        elapsed = int((time.perf_counter() - start) * 1000)
        return OCRServiceResult(raw_text=raw_text, lines=lines, processing_time_ms=elapsed)
