from fastapi import APIRouter, Depends, Response

from hippobox.platform.core.error.auth_exception import AuthErrorCode, auth_error_responses
from hippobox.platform.core.error.inquiry_exception import InquiryErrorCode, inquiry_error_responses
from hippobox.platform.core.error.response_contracts import current_user_error_responses
from hippobox.platform.deps import get_current_admin_user, get_current_user
from hippobox.platform.models.inquiry import (
    InquiryCreate,
    InquiryDetail,
    InquiryPage,
    InquiryReply,
    InquiryStatus,
    InquiryStatusForm,
)
from hippobox.platform.models.user import UserResponse, UserRole
from hippobox.platform.routers.list_query import DEFAULT_PAGE_SIZE, PageQuery, PageSizeQuery
from hippobox.platform.services.inquiry import InquiryService

router = APIRouter()
errors = current_user_error_responses(inquiry_error_responses(*InquiryErrorCode))


@router.get("", response_model=InquiryPage, responses=current_user_error_responses())
async def list_own(
    response: Response,
    page: PageQuery = 1,
    page_size: PageSizeQuery = DEFAULT_PAGE_SIZE,
    status: InquiryStatus | None = None,
    user: UserResponse = Depends(get_current_user),
    service: InquiryService = Depends(),
) -> InquiryPage:
    response.headers["Cache-Control"] = "no-store"
    return await service.list(user.id, False, page, page_size, status)


@router.get(
    "/admin",
    response_model=InquiryPage,
    responses=current_user_error_responses(auth_error_responses(AuthErrorCode.INSUFFICIENT_ROLE)),
)
async def list_all(
    response: Response,
    page: PageQuery = 1,
    page_size: PageSizeQuery = DEFAULT_PAGE_SIZE,
    status: InquiryStatus | None = None,
    user: UserResponse = Depends(get_current_admin_user),
    service: InquiryService = Depends(),
) -> InquiryPage:
    response.headers["Cache-Control"] = "no-store"
    return await service.list(user.id, True, page, page_size, status)


@router.post("", response_model=InquiryDetail, responses=errors)
async def create(
    form: InquiryCreate,
    response: Response,
    user: UserResponse = Depends(get_current_user),
    service: InquiryService = Depends(),
) -> InquiryDetail:
    response.headers["Cache-Control"] = "no-store"
    return await service.create(user.id, form)


@router.get("/{inquiry_id}", response_model=InquiryDetail, responses=errors)
async def detail(
    inquiry_id: int,
    response: Response,
    user: UserResponse = Depends(get_current_user),
    service: InquiryService = Depends(),
) -> InquiryDetail:
    response.headers["Cache-Control"] = "no-store"
    return await service.detail(inquiry_id, user.id, user.role == UserRole.ADMIN)


@router.post("/{inquiry_id}/messages", response_model=InquiryDetail, responses=errors)
async def reply(
    inquiry_id: int,
    form: InquiryReply,
    response: Response,
    user: UserResponse = Depends(get_current_user),
    service: InquiryService = Depends(),
) -> InquiryDetail:
    response.headers["Cache-Control"] = "no-store"
    return await service.reply(inquiry_id, user.id, user.role == UserRole.ADMIN, form)


@router.patch(
    "/{inquiry_id}/status",
    response_model=InquiryDetail,
    responses=current_user_error_responses(
        {
            **inquiry_error_responses(*InquiryErrorCode),
            **auth_error_responses(AuthErrorCode.INSUFFICIENT_ROLE),
        }
    ),
)
async def change_status(
    inquiry_id: int,
    form: InquiryStatusForm,
    response: Response,
    user: UserResponse = Depends(get_current_admin_user),
    service: InquiryService = Depends(),
) -> InquiryDetail:
    response.headers["Cache-Control"] = "no-store"
    return await service.status(inquiry_id, user.id, form.status)
