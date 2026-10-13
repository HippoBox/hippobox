from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import StreamingResponse

from hippobox.platform.core.error.response_contracts import current_user_error_responses
from hippobox.platform.deps import get_current_user
from hippobox.platform.models.user import UserResponse
from hippobox.platform.services.realtime import RealtimeService

router = APIRouter()


@router.get(
    "/stream",
    response_class=StreamingResponse,
    responses={
        **current_user_error_responses(),
        status.HTTP_200_OK: {
            "description": "SSE frames; each data field contains a RealtimeStreamEvent JSON value. "
            "No replay is provided; re-fetch affected resources after reconnecting.",
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "x-sse-event-schema": {"$ref": "#/components/schemas/RealtimeStreamEvent"},
                }
            },
        },
    },
)
async def stream_events(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    service: RealtimeService = Depends(RealtimeService),
    last_event_id: str | None = Header(
        default=None, description="Accepted for diagnostics only; events are not replayed."
    ),
) -> StreamingResponse:
    stream = service.stream_user_events(
        request=request,
        current_user=current_user,
        last_event_id=last_event_id,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
