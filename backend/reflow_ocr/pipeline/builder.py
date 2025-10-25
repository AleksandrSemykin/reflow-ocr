"""Document assembly helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from ..schemas.document import Document, DocumentBlock, DocumentPage


def build_document(pages: Iterable[DocumentPage]) -> Document:
    return Document(created_at=datetime.utcnow(), pages=list(pages))


def make_page(index: int, image: np.ndarray, blocks: list[DocumentBlock]) -> DocumentPage:
    height, width = image.shape[:2]
    return DocumentPage(index=index, width=width, height=height, blocks=blocks)
