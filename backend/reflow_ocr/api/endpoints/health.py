"""Health-check endpoints."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter

from ...core.config import settings

router = APIRouter()


@router.get("/", summary="Service health status")
def healthcheck() -> dict[str, str | Literal["ok"]]:
    """Return static metadata for uptime probes."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.env,
        "dataDir": str(settings.data_dir),
    }
