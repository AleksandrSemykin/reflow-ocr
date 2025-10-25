"""Root API router."""

from fastapi import APIRouter

from .endpoints import health, sessions

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
