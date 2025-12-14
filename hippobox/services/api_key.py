import logging

from fastapi import Request

from hippobox.errors.api_key import ApiKeyErrorCode
from hippobox.errors.service import raise_exception_with_log
from hippobox.models.api_key import APIKeyCreatedResponse, APIKeyForm, APIKeyResponse, APIKeys, APIKeyUpdate

log = logging.getLogger("apikey")


class ApiKeyService:
    async def create_key(self, user_id: int, name: str) -> APIKeyCreatedResponse:
        try:
            form = APIKeyForm(user_id=user_id, name=name)

            return await APIKeys.create(form)

        except Exception as e:
            raise_exception_with_log(ApiKeyErrorCode.CREATE_FAILED, e)

    async def list_keys(self, user_id: int) -> list[APIKeyResponse]:
        try:
            return await APIKeys.get_list_by_user(user_id)
        except Exception as e:
            log.error(f"Failed to list API keys for user {user_id}: {e}")
            return []

    async def update_key(self, user_id: int, key_id: int, form: APIKeyUpdate) -> APIKeyResponse:
        updated_key = await APIKeys.update(key_id, user_id, form)

        if updated_key is None:
            raise_exception_with_log(ApiKeyErrorCode.UPDATE_FAILED)

        return updated_key

    async def delete_key(self, user_id: int, key_id: int) -> None:
        success = await APIKeys.delete(key_id, user_id)

        if not success:
            raise_exception_with_log(ApiKeyErrorCode.DELETE_FAILED)


def get_api_key_service(request: Request) -> ApiKeyService:
    return ApiKeyService()
