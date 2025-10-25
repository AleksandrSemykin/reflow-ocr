"""Disk persistence helpers for sessions and pages."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable
from uuid import UUID

from ..schemas.session import SessionDetail


class SessionRepository:
    """Handles serialization of session objects and their assets to disk."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.sessions_dir = self.root / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: UUID) -> Path:
        return self.sessions_dir / str(session_id)

    def load_all(self) -> Iterable[SessionDetail]:
        for child in self.sessions_dir.iterdir():
            if not child.is_dir():
                continue
            manifest = child / "session.json"
            if not manifest.exists():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                yield SessionDetail.model_validate(data)
            except Exception:
                continue

    def save(self, session: SessionDetail) -> None:
        manifest_dir = self._session_dir(session.id)
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest = manifest_dir / "session.json"
        manifest.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def delete(self, session_id: UUID) -> None:
        target = self._session_dir(session_id)
        if target.exists():
            shutil.rmtree(target)

    def pages_dir(self, session_id: UUID) -> Path:
        path = self._session_dir(session_id) / "pages"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def page_path(self, session_id: UUID, filename: str) -> Path:
        return self.pages_dir(session_id) / filename
