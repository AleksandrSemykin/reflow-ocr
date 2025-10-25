"""Markdown exporter."""

from __future__ import annotations

from dataclasses import dataclass

from ..schemas.document import Document, DocumentPage
from .base import DocumentExporter, ExportFormat, ExportRequest, ExportResult


@dataclass
class MarkdownExporter(DocumentExporter):
    format: ExportFormat = ExportFormat.MARKDOWN

    def export(self, document: Document, request: ExportRequest) -> ExportResult:
        lines: list[str] = ["# Распознанный документ", ""]
        for page in document.pages:
            self._render_page(lines, page)
        content = "\n".join(lines).encode("utf-8")
        filename = f"{request.filename_hint}.md"
        return ExportResult(filename=filename, media_type="text/markdown; charset=utf-8", content=content)

    def _render_page(self, lines: list[str], page: DocumentPage) -> None:
        lines.append(f"## Страница {page.index + 1}")
        for block in page.blocks:
            text = "\n".join(span.text for span in block.spans if span.text).strip()
            if not text:
                continue
            if block.type == "header":
                lines.append(f"**{text}**")
            else:
                lines.append(text)
            lines.append("")
