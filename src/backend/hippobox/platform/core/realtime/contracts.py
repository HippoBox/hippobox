"""JSON data schemas carried inside SSE frames (not JSON HTTP responses)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

from hippobox.platform.core.realtime.domain_events.api_key import APIKeyRealtimeEventType
from hippobox.platform.core.realtime.events import RealtimeEvent
from hippobox.platform.models.api_key import APIKeyResponse


class ConnectedPayload(BaseModel):
    user_id: int
    channel: str


class ConnectedEvent(RealtimeEvent):
    type: Literal["connected"]
    payload: ConnectedPayload


class PingEvent(RealtimeEvent):
    type: Literal["ping"]


class APIKeyEventPayload(BaseModel):
    api_key: APIKeyResponse


class APIKeyEvent(RealtimeEvent):
    type: Literal[
        APIKeyRealtimeEventType.CREATED,
        APIKeyRealtimeEventType.STATUS_UPDATED,
        APIKeyRealtimeEventType.DELETED,
    ]
    payload: APIKeyEventPayload


class InboxChangedEvent(RealtimeEvent):
    type: Literal["inbox.changed"]


class RealtimeStreamEvent(
    RootModel[
        Annotated[
            ConnectedEvent | PingEvent | APIKeyEvent | InboxChangedEvent,
            Field(discriminator="type"),
        ]
    ]
):
    pass
