"""Asynchronous task manager with SSE broadcasting."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict
from uuid import UUID, uuid4


TaskCoroutine = Callable[[], Awaitable[Any]]


@dataclass(frozen=True)
class TaskMeta:
    id: UUID
    session_id: UUID
    kind: str
    created_at: datetime


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: Dict[UUID, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    async def subscribe(self, session_id: UUID) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers[session_id].add(queue)
        await queue.put(
            {
                "event": "connected",
                "sessionId": str(session_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return queue

    def unsubscribe(self, session_id: UUID, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.get(session_id, set()).discard(queue)

    async def publish(self, session_id: UUID, payload: dict[str, Any]) -> None:
        queues = list(self._subscribers.get(session_id, []))
        for queue in queues:
            await queue.put(payload)


class TaskManager:
    """Runs background coroutines per session and streams events."""

    def __init__(self) -> None:
        self._tasks: dict[UUID, asyncio.Task[Any]] = {}
        self._task_meta: dict[UUID, TaskMeta] = {}
        self._broker = EventBroker()

    async def subscribe(self, session_id: UUID) -> asyncio.Queue[dict[str, Any]]:
        return await self._broker.subscribe(session_id)

    def unsubscribe(self, session_id: UUID, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._broker.unsubscribe(session_id, queue)

    async def publish(self, session_id: UUID, payload: dict[str, Any]) -> None:
        await self._broker.publish(session_id, payload)

    def is_task_running(self, task_id: UUID) -> bool:
        task = self._tasks.get(task_id)
        return bool(task and not task.done())

    async def start_task(self, session_id: UUID, kind: str, coroutine_factory: TaskCoroutine) -> UUID:
        task_id = uuid4()
        meta = TaskMeta(id=task_id, session_id=session_id, kind=kind, created_at=datetime.now(timezone.utc))

        async def runner() -> None:
            await self.publish(
                session_id,
                {
                    "event": "task-started",
                    "taskId": str(task_id),
                    "kind": kind,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            try:
                await coroutine_factory()
                await self.publish(
                    session_id,
                    {
                        "event": "task-completed",
                        "taskId": str(task_id),
                        "kind": kind,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except asyncio.CancelledError:
                await self.publish(
                    session_id,
                    {
                        "event": "task-cancelled",
                        "taskId": str(task_id),
                        "kind": kind,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                raise
            except Exception as exc:
                await self.publish(
                    session_id,
                    {
                        "event": "task-failed",
                        "taskId": str(task_id),
                        "kind": kind,
                        "error": str(exc),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                raise
            finally:
                self._tasks.pop(task_id, None)
                self._task_meta.pop(task_id, None)

        task = asyncio.create_task(runner())
        self._tasks[task_id] = task
        self._task_meta[task_id] = meta
        return task_id

    def cancel_task(self, task_id: UUID) -> None:
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()

    async def stream(self, session_id: UUID) -> AsyncGenerator[str, None]:
        queue = await self.subscribe(session_id)
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    payload = {
                        "event": "heartbeat",
                        "sessionId": str(session_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                yield f"data: {json.dumps(payload, default=str)}\n\n"
                if payload.get("event") in {"task-completed", "task-failed", "task-cancelled"}:
                    break
        finally:
            self.unsubscribe(session_id, queue)


_TASK_MANAGER_SINGLETON: TaskManager | None = None


def get_task_manager() -> TaskManager:
    global _TASK_MANAGER_SINGLETON
    if _TASK_MANAGER_SINGLETON is None:
        _TASK_MANAGER_SINGLETON = TaskManager()
    return _TASK_MANAGER_SINGLETON


def reset_task_manager() -> None:
    global _TASK_MANAGER_SINGLETON
    _TASK_MANAGER_SINGLETON = None
