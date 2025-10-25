"""Exporter registry."""

from __future__ import annotations

from dataclasses import dataclass

from .base import DocumentExporter, ExportFormat, ExportRequest, ExportResult
from .docx import DocxExporter
from .markdown import MarkdownExporter
from .pdf import PdfExporter


class ExporterRegistry:
    """Resolves exporters by format."""

    def __init__(self) -> None:
        self._registry: dict[ExportFormat, DocumentExporter] = {
            ExportFormat.DOCX: DocxExporter(),
            ExportFormat.MARKDOWN: MarkdownExporter(),
            ExportFormat.PDF: PdfExporter(),
        }

    def export(self, document, request: ExportRequest) -> ExportResult:
        exporter = self._registry.get(request.format)
        if not exporter:
            raise ValueError(f"Unsupported export format: {request.format}")
        return exporter.export(document, request)
