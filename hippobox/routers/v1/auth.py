from fastapi import APIRouter, Body, Depends

from hippobox.errors.auth import AuthException
from hippobox.errors.service import exceptions_to_http
from hippobox.models.user import LoginForm, SignupForm, TokenResponse, UserResponse
from hippobox.services.auth import AuthService, get_auth_service
from hippobox.utils.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user


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

        user (UserResponse): The successfully created user object (unverified).

    This endpoint creates a DB entry, hashes the password,
    and triggers an asynchronous email verification process.
    """
    try:
        return await service.signup(form)
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Login
# -----------------------------
@router.post("/login", response_model=TokenResponse)
async def login(
    form: LoginForm,
    service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a user and issue a JWT access token.

    ### Args:

        form (LoginForm): Email and password credentials.

    ### Returns:

        token (TokenResponse): Access token, type, and user info.

    This endpoint:
    - Verifies credentials against the database.
    - Checks for Redis-based login limits (brute-force protection).
    - Updates last login timestamp.
    """
    try:
        return await service.login(form)
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Logout
# -----------------------------
@router.post("/logout")
async def logout(
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
        await service.logout(current_user.id)
        return {"message": "Successfully logged out"}
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Refresh Token
# -----------------------------
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    user_id: int = Body(..., embed=True),
    service: AuthService = Depends(get_auth_service),
):
    """
    Renew access token using a valid refresh token.

    ### Args:

        refresh_token (str): The refresh token issued during login.
        user_id (int): The ID of the user owning the token.

    ### Returns:

        token (TokenResponse): A new pair of Access and Refresh tokens.

    This endpoint implements **Refresh Token Rotation**.
    The old refresh token is invalidated, and a completely new pair is issued.
    """
    try:
        return await service.refresh_access_token(refresh_token, user_id)
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Verify Email
# -----------------------------
@router.get("/verify-email/{token}", response_model=UserResponse)
async def verify_email(
    token: str,
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
        return await service.verify_email(token)
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Password Reset: Request
# -----------------------------
@router.post("/password-reset/request")
async def request_password_reset(
    email: str = Body(..., embed=True),
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
        await service.request_password_reset(email)
        return {"message": "If the email exists, a reset link has been sent."}
    except AuthException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Password Reset: Confirm
# -----------------------------
@router.post("/password-reset/confirm")
async def reset_password(
    token: str = Body(...),
    new_password: str = Body(...),
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
        await service.reset_password(token, new_password)
        return {"message": "Password has been reset successfully."}
    except AuthException as e:
        raise exceptions_to_http(e)
