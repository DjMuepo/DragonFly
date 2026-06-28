from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

JobHandler = Callable[[str], Awaitable[None]]

@dataclass
class JobQueue:
    """Minimal async job queue skeleton for MVP.

    - In production, replace with Cloud Tasks / PubSub / Celery / Redis queue.
    - Keeps heavy work off the request thread.
    """
    handler: JobHandler
    _q: asyncio.Queue[str] = asyncio.Queue()
    _task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._worker())

    async def enqueue(self, job_id: str) -> None:
        await self._q.put(job_id)

    async def _worker(self) -> None:
        while True:
            job_id = await self._q.get()
            try:
                await self.handler(job_id)
            except Exception:
                # swallow errors; handler should mark job as error
                pass
            finally:
                self._q.task_done()
