from fastapi import APIRouter, Depends, Path

from hippobox.errors.admin import AdminException
from hippobox.errors.service import exceptions_to_http
from hippobox.models.user import UserModel, UserResponse
from hippobox.services.admin import AdminService, get_admin_service
from hippobox.utils.auth import require_admin

router = APIRouter()


@router.get("/users", response_model=list[UserModel])
async def list_users(
    _: UserResponse = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
):
    """
    Retrieve all users (admin-only).
    """
    try:
        return await service.list_users()
    except AdminException as e:
        raise exceptions_to_http(e)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int = Path(..., description="ID of the user to delete"),
    _: UserResponse = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
):
    """
    Permanently delete a user and related data.
    """
    try:
        await service.delete_user(user_id)
        return {"message": "User deleted successfully."}
    except AdminException as e:
        raise exceptions_to_http(e)
