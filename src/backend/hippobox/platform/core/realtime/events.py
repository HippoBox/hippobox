from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class RealtimeEventType(StrEnum):
    CONNECTED = "connected"
    PING = "ping"


class RealtimeEvent(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    type: str
    version: str = "v1"
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)


def build_realtime_event(
    event_type: RealtimeEventType | str,
    payload: Mapping[str, Any] | None = None,
) -> RealtimeEvent:
    return RealtimeEvent(type=str(event_type), payload=dict(payload or {}))


def encode_sse_event(event: RealtimeEvent, *, retry_millis: int | None = None) -> str:
    lines: list[str] = []
    if retry_millis is not None:
        lines.append(f"retry: {retry_millis}")
    lines.append(f"id: {event.id}")
    lines.append(f"event: {event.type}")
    lines.append(f"data: {event.model_dump_json()}")
    return "\n".join(lines) + "\n\n"
