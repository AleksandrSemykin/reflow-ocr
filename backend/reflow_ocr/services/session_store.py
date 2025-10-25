"""Session storage, persistence, and asset management."""

from __future__ import annotations

import atexit
import io
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Iterable
from uuid import UUID, uuid4

from PIL import Image

from ..core.config import settings
from ..schemas.session import (
    PageMetadata,
    SessionCreate,
    SessionDetail,
    SessionPage,
    SessionSummary,
    SessionUpdate,
)
from ..schemas.document import Document
from .session_repository import SessionRepository


class SessionStore:
    """Keeps session metadata in memory while persisting changes to disk."""

    def __init__(self) -> None:
        self._repository = SessionRepository(settings.data_dir)
        self._sessions: dict[UUID, SessionDetail] = {
            session.id: session for session in self._repository.load_all()
        }
        self._lock = RLock()
        self._dirty_sessions: set[UUID] = set()
        self._autosave_interval = max(settings.autosave_interval_seconds, 5)
        self._stop_event = Event()
        self._autosave_thread = Thread(target=self._autosave_loop, daemon=True)
        self._autosave_thread.start()
        atexit.register(self.shutdown)

    # ------------------------------------------------------------------ helpers
    def _autosave_loop(self) -> None:
        while not self._stop_event.wait(self._autosave_interval):
            self.flush()
        self.flush()

    def _mark_dirty(self, session_id: UUID) -> None:
        self._dirty_sessions.add(session_id)

    def flush(self) -> None:
        with self._lock:
            for session_id in list(self._dirty_sessions):
                session = self._sessions.get(session_id)
                if session:
                    self._repository.save(session)
            self._dirty_sessions.clear()

    # ------------------------------------------------------------------ CRUD
    def list(self) -> Iterable[SessionSummary]:
        with self._lock:
            return sorted(
                self._sessions.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )

    def get(self, session_id: UUID) -> SessionDetail:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError(f"Session {session_id} not found")
            return session

    def create(self, payload: SessionCreate) -> SessionDetail:
        now = datetime.now(timezone.utc)
        session = SessionDetail(
            id=uuid4(),
            name=payload.name or f"Session {now.strftime('%Y-%m-%d %H:%M:%S')}",
            description=payload.description,
            created_at=now,
            updated_at=now,
            page_count=0,
            status="draft",
            autosave_enabled=True,
            pages=[],
        )
        with self._lock:
            self._sessions[session.id] = session
            self._mark_dirty(session.id)
        return session

    def update(self, session_id: UUID, payload: SessionUpdate) -> SessionDetail:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError(f"Session {session_id} not found")
            attrs = {
                "updated_at": datetime.now(timezone.utc),
            }
            if payload.name:
                attrs["name"] = payload.name
            if payload.description is not None:
                attrs["description"] = payload.description
            updated = session.model_copy(update=attrs)
            self._sessions[session_id] = updated
            self._mark_dirty(session_id)
            return updated

    def delete(self, session_id: UUID) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._dirty_sessions.discard(session_id)
        self._repository.delete(session_id)

    # ------------------------------------------------------------------ pages
    def add_page(
        self,
        session_id: UUID,
        *,
        data: bytes,
        original_name: str,
        source_type: str,
        mimetype: str | None,
    ) -> SessionPage:
        session = self.get(session_id)
        page_id = uuid4()
        extension = _resolve_extension(original_name, mimetype)
        filename = f"{page_id}{extension}"
        dest_path = self._repository.page_path(session_id, filename)
        dest_path.write_bytes(data)

        metadata = _extract_metadata(data, mimetype)
        index = len(session.pages)
        page = SessionPage(
            id=page_id,
            index=index,
            filename=filename,
            original_name=original_name or filename,
            source_type=source_type,  # type: ignore[arg-type]
            metadata=metadata,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        updated_session = session.model_copy(
            update={
                "pages": [*session.pages, page],
                "page_count": len(session.pages) + 1,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        with self._lock:
            self._sessions[session_id] = updated_session
            self._mark_dirty(session_id)
        return page

    def reorder_pages(self, session_id: UUID, new_order: list[UUID]) -> SessionDetail:
        session = self.get(session_id)
        id_to_page = {page.id: page for page in session.pages}
        reordered = []
        for idx, page_id in enumerate(new_order):
            page = id_to_page.get(page_id)
            if not page:
                continue
            reordered.append(page.model_copy(update={"index": idx, "updated_at": datetime.now(timezone.utc)}))
        updated = session.model_copy(
            update={
                "pages": reordered,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        with self._lock:
            self._sessions[session_id] = updated
            self._mark_dirty(session_id)
        return updated

    def remove_page(self, session_id: UUID, page_id: UUID) -> SessionDetail:
        session = self.get(session_id)
        remaining = [page for page in session.pages if page.id != page_id]
        if len(remaining) == len(session.pages):
            return session
        for idx, page in enumerate(remaining):
            remaining[idx] = page.model_copy(
                update={"index": idx, "updated_at": datetime.now(timezone.utc)}
            )
        updated = session.model_copy(
            update={
                "pages": remaining,
                "page_count": len(remaining),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        with self._lock:
            self._sessions[session_id] = updated
            self._mark_dirty(session_id)
        return updated

    def page_path(self, session_id: UUID, page_id: UUID) -> str:
        session = self.get(session_id)
        page = next((p for p in session.pages if p.id == page_id), None)
        if not page:
            raise KeyError(f"Page {page_id} not found in session {session_id}")
        return str(self._repository.page_path(session_id, page.filename))

    def export_archive(self, session_id: UUID) -> Path:
        session = self.get(session_id)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".reflow-session")
        tmp_path = Path(tmp.name)
        tmp.close()
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("session.json", session.model_dump_json(indent=2))
            for page in session.pages:
                page_path = self._repository.page_path(session_id, page.filename)
                if Path(page_path).exists():
                    archive.write(page_path, arcname=f"pages/{page.filename}")
        return tmp_path

    def import_archive(self, data: bytes) -> SessionDetail:
        buffer = io.BytesIO(data)
        with zipfile.ZipFile(buffer, "r") as archive:
            try:
                manifest = json.loads(archive.read("session.json"))
            except KeyError as exc:
                raise ValueError("Archive missing session.json") from exc
            source_session = SessionDetail.model_validate(manifest)
            page_payloads: dict[str, bytes] = {}
            for page in source_session.pages:
                try:
                    page_payloads[page.filename] = archive.read(f"pages/{page.filename}")
                except KeyError:
                    page_payloads[page.filename] = b""

        now = datetime.now(timezone.utc)
        new_id = uuid4()
        new_pages: list[SessionPage] = []
        for idx, page in enumerate(source_session.pages):
            new_page_id = uuid4()
            extension = _resolve_extension(page.filename, page.metadata.mimetype)
            filename = f"{new_page_id}{extension}"
            dest_path = self._repository.page_path(new_id, filename)
            dest_path.write_bytes(page_payloads.get(page.filename, b""))
            new_pages.append(
                SessionPage(
                    id=new_page_id,
                    index=idx,
                    filename=filename,
                    original_name=page.original_name,
                    source_type=page.source_type,
                    metadata=page.metadata,
                    created_at=now,
                    updated_at=now,
                )
            )

        imported = source_session.model_copy(
            update={
                "id": new_id,
                "name": f"{source_session.name} (imported)",
                "created_at": now,
                "updated_at": now,
                "pages": new_pages,
                "page_count": len(new_pages),
                "status": "draft",
                "document": None,
                "last_error": None,
                "last_recognized_at": None,
            }
        )
        with self._lock:
            self._sessions[new_id] = imported
            self._mark_dirty(new_id)
        return imported

    def mark_processing(self, session_id: UUID) -> SessionDetail:
        session = self.get(session_id)
        updated = session.model_copy(
            update={
                "status": "processing",
                "last_error": None,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        with self._lock:
            self._sessions[session_id] = updated
            self._mark_dirty(session_id)
        return updated

    def save_document(self, session_id: UUID, document: Document) -> SessionDetail:
        session = self.get(session_id)
        now = datetime.now(timezone.utc)
        updated = session.model_copy(
            update={
                "document": document,
                "status": "ready",
                "last_recognized_at": now,
                "updated_at": now,
                "last_error": None,
            }
        )
        with self._lock:
            self._sessions[session_id] = updated
            self._mark_dirty(session_id)
        return updated

    def mark_error(self, session_id: UUID, message: str) -> SessionDetail:
        session = self.get(session_id)
        updated = session.model_copy(
            update={
                "status": "error",
                "last_error": message,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        with self._lock:
            self._sessions[session_id] = updated
            self._mark_dirty(session_id)
        return updated

    # ------------------------------------------------------------------ lifecycle
    def shutdown(self) -> None:
        self._stop_event.set()
        if self._autosave_thread.is_alive():
            self._autosave_thread.join(timeout=2)
        self.flush()


def _resolve_extension(original_name: str, mimetype: str | None) -> str:
    suffix = ""
    if "." in original_name:
        suffix = "." + original_name.split(".")[-1].lower()
    if suffix:
        return suffix
    if mimetype == "image/jpeg":
        return ".jpg"
    if mimetype == "image/png":
        return ".png"
    return ".bin"


def _extract_metadata(data: bytes, mimetype: str | None) -> PageMetadata:
    try:
        with Image.open(io.BytesIO(data)) as img:
            dpi_value = None
            dpi_info = img.info.get("dpi")
            if isinstance(dpi_info, tuple):
                dpi_value = int(dpi_info[0])
            width, height = img.size
            return PageMetadata(width=width, height=height, dpi=dpi_value, mimetype=mimetype or img.get_format_mimetype())
    except Exception:
        return PageMetadata(mimetype=mimetype)


_SESSION_STORE_SINGLETON: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _SESSION_STORE_SINGLETON
    if _SESSION_STORE_SINGLETON is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _SESSION_STORE_SINGLETON = SessionStore()
    return _SESSION_STORE_SINGLETON


def reset_session_store() -> None:
    global _SESSION_STORE_SINGLETON
    if _SESSION_STORE_SINGLETON is not None:
        _SESSION_STORE_SINGLETON.shutdown()
    _SESSION_STORE_SINGLETON = None
