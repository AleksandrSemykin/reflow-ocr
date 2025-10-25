"""Document schema definitions for recognized output."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TextSpan(BaseModel):
    """Piece of text with positional information."""

    text: str
    confidence: float = 0.0
    bbox: list[int] = Field(default_factory=lambda: [0, 0, 0, 0])  # x, y, w, h


class DocumentBlock(BaseModel):
    """Block of text such as paragraph, header, table cell, etc."""

    id: str
    type: Literal["paragraph", "header", "footer", "table", "figure"] = "paragraph"
    bbox: list[int] = Field(default_factory=lambda: [0, 0, 0, 0])
    spans: list[TextSpan] = Field(default_factory=list)


class DocumentPage(BaseModel):
    """Single document page."""

    index: int
    width: int
    height: int
    blocks: list[DocumentBlock] = Field(default_factory=list)


class Document(BaseModel):
    """Full recognized document."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    language_hint: str = "rus+eng"
    pages: list[DocumentPage] = Field(default_factory=list)
