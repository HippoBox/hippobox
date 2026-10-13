from fastapi import APIRouter, Depends

from hippobox.platform.core.error import APIKeyErrorCode, api_key_error_responses
from hippobox.platform.core.error.response_contracts import current_user_error_responses
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.deps import get_current_user
from hippobox.platform.models.api_key import (
    APIKeyCreateForm,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeysResponse,
    APIKeyStatusUpdateForm,
)
from hippobox.platform.models.user import UserResponse
from hippobox.platform.services.api_key import APIKeyService

router = APIRouter()
logger = get_logger("hippobox.platform.router.api_key")


@router.post(
    "",
    response_model=APIKeyCreateResponse,
    responses=current_user_error_responses(
        api_key_error_responses(
            APIKeyErrorCode.API_KEY_CREATE_FAILED,
            APIKeyErrorCode.API_KEY_NAME_ALREADY_EXISTS,
        ),
    ),
)
async def create_api_key(
    form: APIKeyCreateForm,
    current_user: UserResponse = Depends(get_current_user),
    service: APIKeyService = Depends(APIKeyService),
) -> APIKeyCreateResponse:
    return await service.create_api_key(user_id=current_user.id, form=form)


@router.get("", response_model=APIKeysResponse, responses=current_user_error_responses())
async def list_api_keys(
    current_user: UserResponse = Depends(get_current_user),
    service: APIKeyService = Depends(APIKeyService),
) -> APIKeysResponse:
    keys = await service.list_api_keys(user_id=current_user.id)
    logger.debug("API key list fetched (user_id=%s, count=%s).", current_user.id, len(keys.items))
    return keys


@router.delete(
    "/{api_key_id}",
    response_model=APIKeyResponse,
    responses=current_user_error_responses(
        api_key_error_responses(APIKeyErrorCode.API_KEY_NOT_FOUND),
    ),
)
async def delete_api_key(
    api_key_id: int,
    current_user: UserResponse = Depends(get_current_user),
    service: APIKeyService = Depends(APIKeyService),
) -> APIKeyResponse:
    return await service.delete_api_key(user_id=current_user.id, api_key_id=api_key_id)


@router.patch(
    "/{api_key_id}/status",
    response_model=APIKeyResponse,
    responses=current_user_error_responses(
        api_key_error_responses(
            APIKeyErrorCode.API_KEY_NOT_FOUND,
            APIKeyErrorCode.API_KEY_UPDATE_FAILED,
        ),
    ),
)
async def update_api_key_status(
    api_key_id: int,
    form: APIKeyStatusUpdateForm,
    current_user: UserResponse = Depends(get_current_user),
    service: APIKeyService = Depends(APIKeyService),
) -> APIKeyResponse:
    return await service.update_api_key_status(
        user_id=current_user.id,
        api_key_id=api_key_id,
        form=form,
    )
