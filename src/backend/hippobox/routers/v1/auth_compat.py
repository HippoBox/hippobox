"""Stable HippoBox URLs backed by the Blueprint account service."""

from fastapi import APIRouter, Depends

from hippobox.models.user import GuideSeenUpdateForm, PasswordResetConfirm, PasswordResetRequest, Users
from hippobox.platform.models.user import UserResponse
from hippobox.platform.services.auth import AuthService
from hippobox.utils.auth import get_current_user

router = APIRouter()


@router.patch("/me/guide", response_model=UserResponse)
async def update_guide(form: GuideSeenUpdateForm, user=Depends(get_current_user)):
    updated = await Users.update(user.id, {"guide_seen": form.seen})
    return UserResponse.model_validate(updated.model_dump())


@router.post("/password-reset/request")
async def request_reset(form: PasswordResetRequest, service: AuthService = Depends(AuthService)):
    await service.request_password_reset(form.email)
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/password-reset/confirm")
async def confirm_reset(form: PasswordResetConfirm, service: AuthService = Depends(AuthService)):
    await service.reset_password(form.token, form.new_password)
    return {"message": "Password reset successfully."}


@router.post("/verify-email/resend")
async def resend_verification(form: PasswordResetRequest, service: AuthService = Depends(AuthService)):
    await service.resend_verification_email(form.email)
    return {"message": "If the email exists, a verification link has been sent."}


@router.get("/verify-email/{token}", response_model=UserResponse)
async def verify_email(token: str, service: AuthService = Depends(AuthService)):
    return await service.verify_email(token)
