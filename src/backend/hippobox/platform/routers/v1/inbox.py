from fastapi import APIRouter, Depends, Response

from hippobox.platform.core.error.inbox_exception import InboxErrorCode, inbox_error_responses
from hippobox.platform.core.error.response_contracts import current_user_error_responses
from hippobox.platform.deps import get_current_user
from hippobox.platform.models.inbox import (
    InboxItem,
    InboxPage,
    InboxReadAllForm,
    InboxSelectionForm,
    InboxSummary,
)
from hippobox.platform.models.user import UserResponse
from hippobox.platform.routers.list_query import DEFAULT_PAGE_SIZE, PageQuery, PageSizeQuery
from hippobox.platform.services.inbox import InboxService

router = APIRouter()


@router.get("", response_model=InboxPage, responses=current_user_error_responses())
async def list_notifications(
    response: Response,
    page: PageQuery = 1,
    page_size: PageSizeQuery = DEFAULT_PAGE_SIZE,
    unread_only: bool = False,
    user: UserResponse = Depends(get_current_user),
    service: InboxService = Depends(),
) -> InboxPage:
    response.headers["Cache-Control"] = "no-store"
    return await service.list(user.id, page, page_size, unread_only)


@router.get("/summary", response_model=InboxSummary, responses=current_user_error_responses())
async def summary(
    response: Response,
    user: UserResponse = Depends(get_current_user),
    service: InboxService = Depends(),
) -> InboxSummary:
    response.headers["Cache-Control"] = "no-store"
    return await service.summary(user.id)


@router.post("/read-all", response_model=InboxSummary, responses=current_user_error_responses())
async def read_all(
    form: InboxReadAllForm,
    response: Response,
    user: UserResponse = Depends(get_current_user),
    service: InboxService = Depends(),
) -> InboxSummary:
    response.headers["Cache-Control"] = "no-store"
    return await service.read_all(user.id, form.through_id)


@router.post(
    "/{notification_id}/read",
    response_model=InboxItem,
    responses=current_user_error_responses(inbox_error_responses(InboxErrorCode.NOT_FOUND)),
)
async def read(
    notification_id: int,
    response: Response,
    user: UserResponse = Depends(get_current_user),
    service: InboxService = Depends(),
) -> InboxItem:
    response.headers["Cache-Control"] = "no-store"
    return await service.read(user.id, notification_id)


@router.post(
    "/read-selected", response_model=InboxSummary, responses=current_user_error_responses()
)
async def read_selected(
    form: InboxSelectionForm,
    response: Response,
    user: UserResponse = Depends(get_current_user),
    service: InboxService = Depends(),
) -> InboxSummary:
    response.headers["Cache-Control"] = "no-store"
    return await service.update_selected(user.id, form.notification_ids, remove=False)


@router.delete("/selected", response_model=InboxSummary, responses=current_user_error_responses())
async def delete_selected(
    form: InboxSelectionForm,
    response: Response,
    user: UserResponse = Depends(get_current_user),
    service: InboxService = Depends(),
) -> InboxSummary:
    response.headers["Cache-Control"] = "no-store"
    return await service.update_selected(user.id, form.notification_ids, remove=True)
