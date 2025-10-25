"""Layout detection heuristics."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import cv2
import numpy as np


@dataclass
class LayoutBlock:
    id: str
    bbox: tuple[int, int, int, int]  # x, y, w, h
    type: str = "paragraph"


class SimpleLayoutAnalyzer:
    """Very lightweight block detector based on contour analysis."""

    def __init__(self, min_area: int = 10_000) -> None:
        self.min_area = min_area

    def analyze(self, image: np.ndarray) -> list[LayoutBlock]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        blocks: list[LayoutBlock] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h < self.min_area:
                continue
            blocks.append(LayoutBlock(id=str(uuid4()), bbox=(x, y, w, h), type="paragraph"))
        if not blocks:
            h, w = image.shape[:2]
            blocks = [LayoutBlock(id=str(uuid4()), bbox=(0, 0, w, h), type="paragraph")]
        blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        for idx, block in enumerate(blocks):
            blocks[idx] = LayoutBlock(id=block.id, bbox=block.bbox, type=block.type)
        return blocks
