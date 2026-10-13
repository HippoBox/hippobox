"""Async-safe producer boundary. Publication errors propagate to the service."""

import asyncio
from uuid import uuid4

from hippobox.platform.core.celery.app import celery_app
from hippobox.platform.core.observability.request_context import get_trace_id


async def publish_task(name: str, *, payload: dict[str, object]) -> str:
    task_id = str(uuid4())
    trace_id = get_trace_id()
    await asyncio.to_thread(
        celery_app.send_task,
        name,
        kwargs=payload,
        task_id=task_id,
        headers={"trace_id": trace_id},
        argsrepr="()",
        kwargsrepr="<redacted>",
    )
    return task_id
