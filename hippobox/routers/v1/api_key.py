from typing import List

from fastapi import APIRouter, Body, Depends, Path

from hippobox.errors.service import exceptions_to_http
from hippobox.models.api_key import APIKeyCreatedResponse, APIKeyResponse, APIKeyUpdate
from hippobox.models.user import UserResponse
from hippobox.services.api_key import ApiKeyService, get_api_key_service
from hippobox.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: UserResponse = Depends(get_current_user),
    service: ApiKeyService = Depends(get_api_key_service),
):
    """
    Get all API keys owned by the current user.
    The response includes `total_requests` but EXCLUDES the raw secret key.
    """
    return await service.list_keys(current_user.id)


@router.post("", response_model=APIKeyCreatedResponse)
async def create_api_key(
    name: str = Body(..., embed=True, description="Name for the new API Key"),
    current_user: UserResponse = Depends(get_current_user),
    service: ApiKeyService = Depends(get_api_key_service),
):
    """
    Create a new API Key.

    **WARNING**: This is the ONLY time the full `secret_key` (sk-...) is returned.
    The client must save it immediately.
    """
    try:
        return await service.create_key(current_user.id, name)
    except Exception as e:
        raise exceptions_to_http(e)


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: int = Path(..., description="ID of the API Key to update"),
    form: APIKeyUpdate = Body(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ApiKeyService = Depends(get_api_key_service),
):
    """
    Update API Key name or active status.
    """
    try:
        return await service.update_key(current_user.id, key_id, form)
    except Exception as e:
        raise exceptions_to_http(e)


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int = Path(..., description="ID of the API Key to delete"),
    current_user: UserResponse = Depends(get_current_user),
    service: ApiKeyService = Depends(get_api_key_service),
):
    """
    Permanently delete an API Key.
    """
    try:
        await service.delete_key(current_user.id, key_id)
        return {"message": "API Key deleted successfully"}
    except Exception as e:
        raise exceptions_to_http(e)
