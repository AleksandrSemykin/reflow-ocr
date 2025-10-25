"""Image preprocessing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def load_image(path: str | Path) -> np.ndarray:
    """Load an image from disk using numpy+cv2 (handles Windows unicode paths)."""
    path = Path(path)
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to decode image at {path}")
    return image


@dataclass
class ImagePreprocessor:
    """Applies denoising + binarization to improve OCR robustness."""

    adaptive_block_size: int = 31
    adaptive_c: int = 10

    def process(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, h=15, templateWindowSize=7, searchWindowSize=21)
        thresh = cv2.adaptiveThreshold(
            denoised,
            maxValue=255,
            adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresholdType=cv2.THRESH_BINARY,
            blockSize=self.adaptive_block_size,
            C=self.adaptive_c,
        )
        deskewed = self._deskew(thresh)
        return cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        coords = np.column_stack(np.where(image < 255))
        if coords.size == 0:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated


def pil_from_cv(image: np.ndarray) -> Image.Image:
    """Convert cv2 image to PIL."""
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
