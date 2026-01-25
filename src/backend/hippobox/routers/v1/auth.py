from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from hippobox.core.email_links import build_verify_email_redirect_url
from hippobox.core.settings import SETTINGS
from hippobox.errors.auth import AuthErrorCode, AuthException
from hippobox.errors.service import exceptions_to_http
from hippobox.models.user import (
    EmailVerificationResend,
    LoginForm,
    LoginTokenResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    ProfileUpdateForm,
    SignupForm,
    TokenRefreshResponse,
    UserResponse,
)
from hippobox.services.auth import AuthService, get_auth_service
from hippobox.utils.auth import get_current_user
from hippobox.utils.cookies import clear_refresh_cookies, get_refresh_cookie_value, set_refresh_cookies

router = APIRouter()


def _raise_login_disabled():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "LOGIN_DISABLED", "message": "Login is disabled"},
    )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    form: ProfileUpdateForm,
    current_user: UserResponse = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Update the current user's profile.
    """
    try:
        return await service.update_profile(current_user.id, form)
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Signup
# -----------------------------
@router.post("/signup", response_model=UserResponse)
async def signup(
    form: SignupForm,
    service: AuthService = Depends(get_auth_service),
):
    """
        Register a new user account.

        The input should include:
        - email: Valid email address
        - password: Raw password (will be hashed)
        - name: User's display name

        ### Returns:
    `
            user (UserResponse): The successfully created user object (unverified).

        This endpoint creates a DB entry, hashes the password,
        and triggers an asynchronous email verification process.
    """
    try:
        if not SETTINGS.LOGIN_ENABLED:
            _raise_login_disabled()
        return await service.signup(form)
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Login
# -----------------------------
@router.post("/login", response_model=LoginTokenResponse)
async def login(
    request: Request,
    response: Response,
    form: LoginForm,
    service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a user and issue a JWT access token.

    ### Args:

        form (LoginForm): Email and password credentials.

    ### Returns:

        token (LoginTokenResponse): Access token, refresh token, type, and user info.

    This endpoint:
    - Verifies credentials against the database.
    - Checks for Redis-based login limits (brute-force protection).
    - Updates last login timestamp.
    """
    try:
        if not SETTINGS.LOGIN_ENABLED:
            _raise_login_disabled()
        token = await service.login(form, request)
        set_refresh_cookies(
            response,
            request,
            token.refresh_token,
            token.user.id,
            remember_me=form.remember_me,
        )
        return token
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Logout
# -----------------------------
@router.post("/logout")
async def logout(
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Log out the current user by invalidating their refresh token.

    ### Requirements:

        Authentication header (Bearer Token) is required.

    ### Returns:

        dict: Success message.

    This removes the refresh token from Redis, effectively preventing
    future access token renewals without re-login.
    """
    try:
        if not SETTINGS.LOGIN_ENABLED:
            _raise_login_disabled()
        await service.logout(current_user.id)
        clear_refresh_cookies(response)
        return {"message": "Successfully logged out"}
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Refresh Token
# -----------------------------
@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Body(None, embed=True),
    user_id: int | None = Body(None, embed=True),
    service: AuthService = Depends(get_auth_service),
):
    """
    Renew access token using a valid refresh token.

    ### Args:

        refresh_token (str): The refresh token issued during login.
        user_id (int): The ID of the user owning the token.

    ### Returns:

        token (TokenRefreshResponse): A new pair of Access and Refresh tokens.

    This endpoint implements **Refresh Token Rotation**.
    The old refresh token is invalidated, and a completely new pair is issued.
    """
    if not SETTINGS.LOGIN_ENABLED:
        _raise_login_disabled()
    cookie_refresh_token, cookie_user_id = get_refresh_cookie_value(request)
    refresh_token_value = refresh_token or cookie_refresh_token
    user_id_value = user_id or cookie_user_id

    if not refresh_token_value or not user_id_value:
        clear_refresh_cookies(response)
        raise exceptions_to_http(AuthException(AuthErrorCode.INVALID__AUTH_TOKEN))

    try:
        numeric_user_id = int(user_id_value)
    except (TypeError, ValueError):
        clear_refresh_cookies(response)
        raise exceptions_to_http(AuthException(AuthErrorCode.INVALID__AUTH_TOKEN))

    try:
        token = await service.refresh_access_token(refresh_token_value, numeric_user_id)
        set_refresh_cookies(response, request, token.refresh_token, numeric_user_id)
        return token
    except AuthException as e:
        clear_refresh_cookies(response)
        raise exceptions_to_http(e)


# -----------------------------
# Verify Email
# -----------------------------
@router.get("/verify-email/{token}", response_model=UserResponse)
async def verify_email(
    token: str,
    redirect: bool = False,
    service: AuthService = Depends(get_auth_service),
):
    """
    Verify a user's email address using a UUID token.

    ### Args:

        token (str): The verification token sent via email.

    ### Returns:

        user (UserResponse): The updated user object with `is_verified=True`.

    This checks the token existence in Redis. If valid,
    it updates the user status in SQL and invalidates the token.
    """
    try:
        user = await service.verify_email(token)
    except AuthException as e:
        if redirect:
            return RedirectResponse(url=build_verify_email_redirect_url(False), status_code=302)
        raise exceptions_to_http(e)

    if redirect:
        return RedirectResponse(url=build_verify_email_redirect_url(True), status_code=302)
    return user


@router.post("/verify-email/resend")
async def resend_verification_email(
    form: EmailVerificationResend,
    service: AuthService = Depends(get_auth_service),
):
    """
    Resend a verification email if the user exists and is not verified.
    """
    try:
        if not SETTINGS.LOGIN_ENABLED:
            _raise_login_disabled()
        await service.resend_verification_email(form.email)
        return {"message": "If the email exists, a verification link has been sent."}
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Password Reset: Request
# -----------------------------
@router.post("/password-reset/request")
async def request_password_reset(
    form: PasswordResetRequest,
    service: AuthService = Depends(get_auth_service),
):
    """
    Initiate the password reset process.

    ### Args:

    email (str): The email address of the account to reset.

    ### Returns:

        dict: Success message (even if email is not found, for security).

    Generates a password reset token in Redis and simulates sending an email.
    """
    try:
        if not SETTINGS.LOGIN_ENABLED:
            _raise_login_disabled()
        await service.request_password_reset(form.email)
        return {"message": "If the email exists, a reset link has been sent."}
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Password Reset: Confirm
# -----------------------------
@router.post("/password-reset/confirm")
async def reset_password(
    form: PasswordResetConfirm,
    service: AuthService = Depends(get_auth_service),
):
    """
    Complete the password reset process.

    ### Args:

    token (str): The valid reset token.
    new_password (str): The new password to set.

    ### Returns:

        dict: Status message indicating success.

    Verifies the token from Redis, hashes the new password,
    updates the database, and deletes the token.
    """
    try:
        if not SETTINGS.LOGIN_ENABLED:
            _raise_login_disabled()
        await service.reset_password(form.token, form.new_password)
        return {"message": "Password has been reset successfully."}
    except AuthException as e:
        raise exceptions_to_http(e)
