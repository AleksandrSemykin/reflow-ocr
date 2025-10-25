"""Base exporter definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Literal
from uuid import UUID

from ..schemas.document import Document


class ExportFormat(str, Enum):
    DOCX = "docx"
    PDF = "pdf"
    MARKDOWN = "markdown"


@dataclass(slots=True)
class ExportRequest:
    session_id: UUID
    format: ExportFormat
    filename_hint: str = "document"


@dataclass(slots=True)
class ExportResult:
    filename: str
    media_type: str
    content: bytes


class DocumentExporter(ABC):
    format: ExportFormat

    @abstractmethod
    def export(self, document: Document, request: ExportRequest) -> ExportResult:
        ...
