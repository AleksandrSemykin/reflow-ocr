"""OCR engine abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from ..core.config import settings
from ..schemas.document import DocumentBlock, TextSpan
from .layout import LayoutBlock
from .preprocess import pil_from_cv

try:
    import pytesseract  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None
else:
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = str(settings.tesseract_cmd)


class OCREngine(Protocol):
    name: str

    def recognize(self, image: np.ndarray, block: LayoutBlock) -> DocumentBlock:
        ...


@dataclass
class FallbackEngine:
    """Produces placeholder blocks when OCR backends are unavailable."""

    name: str = "fallback"

    def recognize(self, image: np.ndarray, block: LayoutBlock) -> DocumentBlock:
        span = TextSpan(
            text="OCR engine unavailable. Configure Tesseract/PaddleOCR to enable recognition.",
            confidence=0.0,
            bbox=list(block.bbox),
        )
        return DocumentBlock(id=block.id, type=block.type, bbox=list(block.bbox), spans=[span])


@dataclass
class TesseractEngine:
    """Thin wrapper over pytesseract."""

    name: str = "tesseract"
    languages: str = "rus+eng"

    def recognize(self, image: np.ndarray, block: LayoutBlock) -> DocumentBlock:
        if pytesseract is None:
            raise RuntimeError("pytesseract is not installed")
        x, y, w, h = block.bbox
        region = image[y : y + h, x : x + w]
        pil_img = pil_from_cv(region)
        text = pytesseract.image_to_string(pil_img, lang=self.languages)
        clean = text.strip()
        if not clean:
            spans: list[TextSpan] = []
        else:
            spans = [
                TextSpan(
                    text=line.strip(),
                    confidence=0.75,
                    bbox=[x, y + idx * 16, w, 16],
                )
                for idx, line in enumerate(clean.splitlines())
                if line.strip()
            ]
        return DocumentBlock(id=block.id, type=block.type, bbox=list(block.bbox), spans=spans)


class CompositeEngine:
    """Attempts high-quality OCR first, then falls back."""

    def __init__(self) -> None:
        engines: list[OCREngine] = []
        if pytesseract is not None:
            engines.append(TesseractEngine())
        engines.append(FallbackEngine())
        self.engines = engines

    def recognize(self, image: np.ndarray, block: LayoutBlock) -> DocumentBlock:
        last_error: Exception | None = None
        for engine in self.engines:
            try:
                return engine.recognize(image, block)
            except Exception as exc:  # pragma: no cover - diagnostics only
                last_error = exc
                continue
        if last_error:
            span = TextSpan(
                text=f"OCR failed: {last_error}",
                confidence=0.0,
                bbox=list(block.bbox),
            )
        else:
            span = TextSpan(
                text="OCR failed: unknown reason",
                confidence=0.0,
                bbox=list(block.bbox),
            )
        return DocumentBlock(id=block.id, type=block.type, bbox=list(block.bbox), spans=[span])
