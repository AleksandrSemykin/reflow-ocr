"""PDF exporter using ReportLab."""

from __future__ import annotations

import io
from dataclasses import dataclass

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from ..schemas.document import Document, DocumentPage
from .base import DocumentExporter, ExportFormat, ExportRequest, ExportResult


@dataclass
class PdfExporter(DocumentExporter):
    format: ExportFormat = ExportFormat.PDF

    def export(self, document: Document, request: ExportRequest) -> ExportResult:
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        for page in document.pages:
            self._render_page(pdf, page, width, height)
            pdf.showPage()
        pdf.save()
        filename = f"{request.filename_hint}.pdf"
        return ExportResult(filename=filename, media_type="application/pdf", content=buffer.getvalue())

    def _render_page(self, pdf: canvas.Canvas, page: DocumentPage, page_width: float, page_height: float) -> None:
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(40, page_height - 60, f"Страница {page.index + 1}")
        pdf.setFont("Helvetica", 10)
        cursor_y = page_height - 80
        for block in page.blocks:
            for span in block.spans:
                pdf.drawString(50, cursor_y, span.text[:110])
                cursor_y -= 14
                if cursor_y < 80:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 10)
                    cursor_y = page_height - 80
