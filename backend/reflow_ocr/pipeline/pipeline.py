"""Recognition pipeline orchestrator."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable
from uuid import UUID

from ..schemas.document import Document
from ..services.session_store import SessionStore
from .builder import build_document, make_page
from .layout import SimpleLayoutAnalyzer
from .ocr_engines import CompositeEngine
from .preprocess import ImagePreprocessor, load_image

ProgressEmitter = Callable[[dict], Awaitable[None]]


class RecognitionPipeline:
    """Processes session pages into structured documents."""

    def __init__(self) -> None:
        self.preprocessor = ImagePreprocessor()
        self.layout = SimpleLayoutAnalyzer()
        self.ocr = CompositeEngine()

    async def run(self, session_id: UUID, store: SessionStore, emit: ProgressEmitter) -> Document:
        session = store.get(session_id)
        pages = session.pages
        if not pages:
            raise ValueError("Session has no pages to process.")

        await emit({"event": "recognition-start", "sessionId": str(session_id), "totalPages": len(pages)})
        doc_pages = []

        for index, page in enumerate(pages):
            await emit({"event": "page-start", "pageIndex": index})
            image_path = store.page_path(session_id, page.id)
            raw = await asyncio.to_thread(load_image, image_path)
            processed = await asyncio.to_thread(self.preprocessor.process, raw)
            blocks = await asyncio.to_thread(self.layout.analyze, processed)
            doc_blocks = []
            for block in blocks:
                block_result = await asyncio.to_thread(self.ocr.recognize, processed, block)
                doc_blocks.append(block_result)
            doc_pages.append(make_page(index=index, image=processed, blocks=doc_blocks))
            await emit({"event": "page-complete", "pageIndex": index})

        document = build_document(doc_pages)
        await emit({"event": "recognition-finished", "pages": len(doc_pages)})
        store.save_document(session_id, document)
        return document
