"""Session management endpoints."""

import asyncio
import io
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse, Response

from ...schemas.document import Document
from ...schemas.session import (
    PageOrderUpdate,
    ExportPayload,
    SessionCreate,
    SessionDetail,
    SessionSummary,
    SessionUpdate,
)
from ...pipeline import RecognitionPipeline
from ...exporters.base import ExportRequest
from ...exporters.registry import ExporterRegistry
from ...services import SessionStore, get_session_store
from ...services.task_manager import TaskManager, get_task_manager

router = APIRouter()
pipeline = RecognitionPipeline()
exporters = ExporterRegistry()


def _session_not_found(session_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Session {session_id} not found",
    )


def _get_store() -> SessionStore:
    return get_session_store()


def _get_task_manager() -> TaskManager:
    return get_task_manager()


@router.get("/", response_model=list[SessionSummary], summary="List all sessions")
def list_sessions(store: SessionStore = Depends(_get_store)) -> list[SessionSummary]:
    return list(store.list())


@router.post(
    "/",
    response_model=SessionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
)
def create_session(payload: SessionCreate, store: SessionStore = Depends(_get_store)) -> SessionDetail:
    return store.create(payload)


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    summary="Get session details",
)
def read_session(session_id: UUID, store: SessionStore = Depends(_get_store)) -> SessionDetail:
    try:
        return store.get(session_id)
    except KeyError:
        raise _session_not_found(session_id)


@router.patch(
    "/{session_id}",
    response_model=SessionDetail,
    summary="Update session metadata",
)
def update_session(
    session_id: UUID,
    payload: SessionUpdate,
    store: SessionStore = Depends(_get_store),
) -> SessionDetail:
    try:
        return store.update(session_id, payload)
    except KeyError:
        raise _session_not_found(session_id)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
)
def delete_session(session_id: UUID, store: SessionStore = Depends(_get_store)) -> None:
    store.delete(session_id)


@router.post(
    "/{session_id}/pages",
    response_model=SessionDetail,
    summary="Upload pages to a session",
)
async def upload_pages(
    session_id: UUID,
    files: list[UploadFile] = File(...),
    store: SessionStore = Depends(_get_store),
) -> SessionDetail:
    try:
        for upload in files:
            data = await upload.read()
            store.add_page(
                session_id,
                data=data,
                original_name=upload.filename or "page.png",
                source_type="file",
                mimetype=upload.content_type,
            )
        return store.get(session_id)
    except KeyError:
        raise _session_not_found(session_id)


@router.post(
    "/{session_id}/pages/reorder",
    response_model=SessionDetail,
    summary="Reorder pages inside a session",
)
def reorder_pages(
    session_id: UUID,
    payload: PageOrderUpdate,
    store: SessionStore = Depends(_get_store),
) -> SessionDetail:
    try:
        return store.reorder_pages(session_id, payload.order)
    except KeyError:
        raise _session_not_found(session_id)


@router.delete(
    "/{session_id}/pages/{page_id}",
    response_model=SessionDetail,
    summary="Remove page from session",
)
def delete_page(
    session_id: UUID,
    page_id: UUID,
    store: SessionStore = Depends(_get_store),
) -> SessionDetail:
    try:
        return store.remove_page(session_id, page_id)
    except KeyError:
        raise _session_not_found(session_id)


@router.get(
    "/{session_id}/archive",
    response_class=FileResponse,
    summary=".reflow-session archive download",
)
def download_archive(
    session_id: UUID,
    background: BackgroundTasks,
    store: SessionStore = Depends(_get_store),
) -> FileResponse:
    try:
        archive_path = store.export_archive(session_id)
    except KeyError:
        raise _session_not_found(session_id)

    def cleanup(path: str) -> None:
        Path(path).unlink(missing_ok=True)

    background.add_task(cleanup, str(archive_path))
    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename=f"{session_id}.reflow-session",
    )


@router.post(
    "/import",
    response_model=SessionDetail,
    summary="Import .reflow-session archive",
)
async def import_archive(
    file: UploadFile = File(...),
    store: SessionStore = Depends(_get_store),
) -> SessionDetail:
    try:
        data = await file.read()
        return store.import_archive(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/{session_id}/document",
    response_model=Document,
    summary="Retrieve recognized document",
)
def get_document(session_id: UUID, store: SessionStore = Depends(_get_store)) -> Document:
    try:
        session = store.get(session_id)
    except KeyError:
        raise _session_not_found(session_id)
    if not session.document:
        raise HTTPException(status_code=404, detail="Document is not ready yet.")
    return session.document


@router.post(
    "/{session_id}/export",
    summary="Export recognized document",
)
def export_document(
    session_id: UUID,
    payload: ExportPayload,
    store: SessionStore = Depends(_get_store),
) -> Response:
    try:
        session = store.get(session_id)
    except KeyError:
        raise _session_not_found(session_id)
    if not session.document:
        raise HTTPException(status_code=400, detail="Document is not ready yet.")

    filename_hint = session.name.replace(" ", "_").lower() or "document"
    request = ExportRequest(session_id=session_id, format=payload.format, filename_hint=filename_hint)
    try:
        result = exporters.export(session.document, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    headers = {"Content-Disposition": f'attachment; filename="{result.filename}"'}
    return Response(content=result.content, media_type=result.media_type, headers=headers)


@router.get(
    "/{session_id}/events",
    summary="Server-Sent Events stream for session progress",
)
async def session_events(
    session_id: UUID,
    store: SessionStore = Depends(_get_store),
    manager: TaskManager = Depends(_get_task_manager),
) -> StreamingResponse:
    try:
        store.get(session_id)
    except KeyError:
        raise _session_not_found(session_id)
    generator = manager.stream(session_id)
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post(
    "/{session_id}/recognize",
    summary="Start OCR pipeline",
)
async def recognize_session(
    session_id: UUID,
    store: SessionStore = Depends(_get_store),
    manager: TaskManager = Depends(_get_task_manager),
) -> dict[str, str]:
    try:
        store.mark_processing(session_id)
    except KeyError:
        raise _session_not_found(session_id)

    async def run_pipeline() -> None:
        async def emit(payload: dict) -> None:
            await manager.publish(session_id, payload)

        try:
            await pipeline.run(session_id, store, emit)
        except Exception as exc:
            store.mark_error(session_id, str(exc))
            await manager.publish(
                session_id,
                {
                    "event": "recognition-error",
                    "message": str(exc),
                },
            )
            raise

    task_id = await manager.start_task(session_id, "recognition", run_pipeline)
    return {"taskId": str(task_id)}
