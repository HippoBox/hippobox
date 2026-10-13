from urllib.parse import urlencode, urljoin

from fastapi import APIRouter, Body, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.error import AuthErrorCode, AuthException, auth_error_responses
from hippobox.platform.core.error.response_contracts import current_user_error_responses
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.deps import get_current_directory_user, get_current_session_user, get_current_user
from hippobox.platform.models.oauth import OAuthProvider, OAuthProvidersResponse
from hippobox.platform.models.user import (
    AdminUserListResponse,
    ChangePasswordForm,
    DeleteAccountCodeResponse,
    DeleteAccountForm,
    ForgotPasswordForm,
    ForgotPasswordResponse,
    LoginForm,
    LoginResponse,
    RefreshResponse,
    ResendVerificationForm,
    ResendVerificationResponse,
    ResetPasswordForm,
    ResetPasswordResponse,
    SignupForm,
    UpdateProfileForm,
    UserResponse,
    UserRole,
    UserRoleStatsResponse,
    VerifyAccountCodeForm,
    VerifyEmailForm,
    VerifyEmailResponse,
)
from hippobox.platform.routers.list_query import DEFAULT_PAGE_SIZE, PageQuery, PageSizeQuery, SearchQuery
from hippobox.platform.services.auth import AuthService
from hippobox.platform.services.profile_photo import ProfilePhotoService
from hippobox.platform.utils.cookies import clear_refresh_cookies, set_refresh_cookies
from hippobox.platform.utils.token import create_refresh_session_id

router = APIRouter()
logger = get_logger("hippobox.platform.router.auth")

REFRESH_COOKIE_HEADERS = {
    "Set-Cookie": {
        "description": "Two separate Set-Cookie headers: template_refresh_token and "
        "template_refresh_sid; HttpOnly, Path=/; HTTPS uses Secure and SameSite=None, "
        "HTTP uses SameSite=Lax. Persistent expiry is set only with remember_me=true.",
        "schema": {"type": "string"},
    }
}
REDIRECT_HEADERS = {
    "Location": {"description": "Redirect destination", "schema": {"type": "string"}}
}


def _resolve_preferred_language(request: Request) -> str | None:
    app_language = request.headers.get("X-App-Language")
    if app_language and app_language.strip():
        return app_language
    return request.headers.get("Accept-Language")


@router.post(
    "/signup",
    response_model=UserResponse,
    responses=auth_error_responses(
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.EMAIL_ALREADY_EXISTS,
        AuthErrorCode.SIGNUP_FAILED,
    ),
)
async def signup(
    request: Request,
    form: SignupForm,
    service: AuthService = Depends(AuthService),
) -> UserResponse:
    return await service.signup(form, preferred_language=_resolve_preferred_language(request))


@router.get(
    "/oauth/providers",
    response_model=OAuthProvidersResponse,
    responses=auth_error_responses(
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.OAUTH_PROVIDER_NOT_ENABLED,
        AuthErrorCode.OAUTH_PROVIDER_CONFIG_INVALID,
    ),
)
async def oauth_providers(service: AuthService = Depends(AuthService)) -> OAuthProvidersResponse:
    providers = service.get_oauth_provider_public_configs()
    logger.debug("OAuth providers fetched (count=%s).", len(providers))
    return OAuthProvidersResponse(providers=providers)


@router.get(
    "/oauth/{provider}/start",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={
        status.HTTP_307_TEMPORARY_REDIRECT: {"headers": REDIRECT_HEADERS},
        **auth_error_responses(
            AuthErrorCode.LOGIN_DISABLED,
            AuthErrorCode.OAUTH_PROVIDER_NOT_ENABLED,
            AuthErrorCode.OAUTH_PROVIDER_CONFIG_INVALID,
        ),
    },
)
async def oauth_start(
    provider: OAuthProvider,
    request: Request,
    service: AuthService = Depends(AuthService),
) -> RedirectResponse:
    redirect_uri = str(request.url_for("oauth_callback", provider=provider.value))
    authorization_url = await service.build_oauth_authorization_url(provider, redirect_uri)
    return RedirectResponse(url=authorization_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get(
    "/oauth/{provider}/callback",
    name="oauth_callback",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={
        status.HTTP_307_TEMPORARY_REDIRECT: {
            "description": "Success redirects to the frontend and sets refresh cookies. "
            "Provider/domain failures redirect to the frontend failure path with error query parameters.",
            "headers": {**REDIRECT_HEADERS, **REFRESH_COOKIE_HEADERS},
        }
    },
)
async def oauth_callback(
    provider: OAuthProvider,
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    service: AuthService = Depends(AuthService),
) -> RedirectResponse:
    # Provider-side errors are returned as a frontend redirect, not raised as API JSON errors.
    if error:
        logger.error(
            "OAuth callback returned provider error (provider=%s, error=%s).", provider, error
        )
        failure_query = urlencode({"error": error})
        failure_url = urljoin(
            f"{SETTINGS.APP_BASE_URL.rstrip('/')}/",
            SETTINGS.OAUTH_FRONTEND_FAILURE_PATH.lstrip("/"),
        )
        return RedirectResponse(
            url=f"{failure_url}?{failure_query}", status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    # OAuth callback contract requires both authorization code and state.
    try:
        code_value, state_value = service.require_oauth_callback_params(
            provider=provider,
            code=code,
            state=state,
        )
    except AuthException as callback_error:
        logger.error(
            "OAuth callback missing required params (provider=%s, code=%s).",
            provider.value,
            callback_error.code.error,
        )
        failure_query = urlencode(
            {
                "error": callback_error.code.error,
                "message": callback_error.message,
            }
        )
        failure_url = urljoin(
            f"{SETTINGS.APP_BASE_URL.rstrip('/')}/",
            SETTINGS.OAUTH_FRONTEND_FAILURE_PATH.lstrip("/"),
        )
        return RedirectResponse(
            url=f"{failure_url}?{failure_query}", status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    refresh_session_id = create_refresh_session_id()
    try:
        token_payload = await service.oauth_callback_login(
            provider=provider,
            code=code_value,
            state=state_value,
            redirect_uri=str(request.url_for("oauth_callback", provider=provider.value)),
            request=request,
            refresh_session_id=refresh_session_id,
        )
    except AuthException as auth_error:
        # Domain failures are propagated to frontend with code/message query parameters.
        logger.error(
            "OAuth callback login failed (provider=%s, code=%s).",
            provider.value,
            auth_error.code.error,
        )
        failure_query = urlencode(
            {
                "error": auth_error.code.error,
                "message": auth_error.message,
            }
        )
        failure_url = urljoin(
            f"{SETTINGS.APP_BASE_URL.rstrip('/')}/",
            SETTINGS.OAUTH_FRONTEND_FAILURE_PATH.lstrip("/"),
        )
        return RedirectResponse(
            url=f"{failure_url}?{failure_query}", status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    success_url = urljoin(
        f"{SETTINGS.APP_BASE_URL.rstrip('/')}/",
        SETTINGS.OAUTH_FRONTEND_SUCCESS_PATH.lstrip("/"),
    )
    response = RedirectResponse(url=success_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    set_refresh_cookies(
        response=response,
        request=request,
        refresh_token=token_payload.refresh_token,
        refresh_session_id=refresh_session_id,
        remember_me=True,
    )
    return response


@router.post(
    "/token",
    response_model=LoginResponse,
    responses=auth_error_responses(
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.INVALID_CREDENTIALS,
        AuthErrorCode.EMAIL_NOT_VERIFIED,
        AuthErrorCode.ACCOUNT_LOCKED,
    ),
)
async def oauth_token_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(AuthService),
) -> LoginResponse:
    refresh_session_id = create_refresh_session_id()
    form = LoginForm(
        email=form_data.username,
        password=form_data.password,
        remember_me=False,
    )
    return await service.login(form, request, refresh_session_id=refresh_session_id)


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        status.HTTP_200_OK: {"headers": REFRESH_COOKIE_HEADERS},
        **auth_error_responses(
            AuthErrorCode.LOGIN_DISABLED,
            AuthErrorCode.INVALID_CREDENTIALS,
            AuthErrorCode.EMAIL_NOT_VERIFIED,
            AuthErrorCode.ACCOUNT_LOCKED,
        ),
    },
)
async def login(
    request: Request,
    response: Response,
    form: LoginForm,
    service: AuthService = Depends(AuthService),
) -> LoginResponse:
    refresh_session_id = create_refresh_session_id()
    token_payload = await service.login(form, request, refresh_session_id=refresh_session_id)

    set_refresh_cookies(
        response=response,
        request=request,
        refresh_token=token_payload.refresh_token,
        refresh_session_id=refresh_session_id,
        remember_me=form.remember_me,
    )
    return token_payload


@router.get("/me", response_model=UserResponse, responses=current_user_error_responses())
async def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user


@router.get(
    "/admin/user-role-stats",
    response_model=UserRoleStatsResponse,
    responses=current_user_error_responses(
        auth_error_responses(AuthErrorCode.INSUFFICIENT_ROLE),
    ),
)
async def admin_user_role_stats(
    _current_admin_user: UserResponse = Depends(get_current_directory_user),
    service: AuthService = Depends(AuthService),
) -> UserRoleStatsResponse:
    return await service.get_admin_user_role_stats()


@router.get(
    "/admin/users",
    response_model=AdminUserListResponse,
    responses=current_user_error_responses(
        auth_error_responses(
            AuthErrorCode.INSUFFICIENT_ROLE,
            AuthErrorCode.ADMIN_USERS_FAILED,
        )
    ),
)
async def admin_users(
    _current_admin_user: UserResponse = Depends(get_current_directory_user),
    service: AuthService = Depends(AuthService),
    page: PageQuery = 1,
    page_size: PageSizeQuery = DEFAULT_PAGE_SIZE,
    search: SearchQuery = "",
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> AdminUserListResponse:
    return await service.list_admin_users(
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        is_active=is_active,
    )


@router.patch(
    "/me",
    response_model=UserResponse,
    responses=current_user_error_responses(
        auth_error_responses(AuthErrorCode.PROFILE_UPDATE_FAILED),
    ),
)
async def update_me(
    form: UpdateProfileForm,
    current_user: UserResponse = Depends(get_current_user),
    service: AuthService = Depends(AuthService),
) -> UserResponse:
    return await service.update_profile(user_id=current_user.id, form=form)


PASSWORD_CHANGE_ERRORS = current_user_error_responses(
    auth_error_responses(
        AuthErrorCode.INVALID_CREDENTIALS,
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.EMAIL_DISABLED,
        AuthErrorCode.PASSWORD_CHANGE_CODE_INVALID,
        AuthErrorCode.PASSWORD_CHANGE_CODE_THROTTLED,
        AuthErrorCode.PASSWORD_CHANGE_CODE_SEND_FAILED,
        AuthErrorCode.PASSWORD_CHANGE_FAILED,
    )
)


@router.post(
    "/me/password/code", response_model=DeleteAccountCodeResponse, responses=PASSWORD_CHANGE_ERRORS
)
async def request_password_change_code(
    request: Request,
    current_user: UserResponse = Depends(get_current_session_user),
    service: AuthService = Depends(AuthService),
) -> DeleteAccountCodeResponse:
    await service.request_password_change_code(
        current_user.id, request.headers.get("X-App-Language")
    )
    return DeleteAccountCodeResponse(expires_in=600, retry_after=30)


@router.post(
    "/me/password/code/verify",
    response_model=ResetPasswordResponse,
    responses=PASSWORD_CHANGE_ERRORS,
)
async def verify_password_change_code(
    form: VerifyAccountCodeForm,
    current_user: UserResponse = Depends(get_current_session_user),
    service: AuthService = Depends(AuthService),
) -> ResetPasswordResponse:
    await service.verify_account_email_code(current_user.id, form.code, password=True)
    return ResetPasswordResponse(message="Code verified.")


@router.post(
    "/me/deletion-code/verify",
    response_model=ResetPasswordResponse,
    responses=current_user_error_responses(
        auth_error_responses(
            AuthErrorCode.EMAIL_DISABLED,
            AuthErrorCode.LOGIN_DISABLED,
            AuthErrorCode.ACCOUNT_DELETE_CODE_INVALID,
            AuthErrorCode.ACCOUNT_DELETE_FAILED,
        )
    ),
)
async def verify_deletion_code(
    form: VerifyAccountCodeForm,
    current_user: UserResponse = Depends(get_current_session_user),
    service: AuthService = Depends(AuthService),
) -> ResetPasswordResponse:
    await service.verify_account_email_code(current_user.id, form.code, password=False)
    return ResetPasswordResponse(message="Code verified.")


@router.post("/me/password", response_model=ResetPasswordResponse, responses=PASSWORD_CHANGE_ERRORS)
async def change_password(
    form: ChangePasswordForm,
    current_user: UserResponse = Depends(get_current_session_user),
    service: AuthService = Depends(AuthService),
) -> ResetPasswordResponse:
    await service.change_password(current_user.id, form)
    return ResetPasswordResponse(message="Password changed.")


PHOTO_ERRORS = current_user_error_responses(
    auth_error_responses(
        AuthErrorCode.PROFILE_PHOTO_INVALID,
        AuthErrorCode.PROFILE_PHOTO_TOO_LARGE,
        AuthErrorCode.PROFILE_PHOTO_UNAVAILABLE,
        AuthErrorCode.PROFILE_PHOTO_NOT_FOUND,
        AuthErrorCode.PROFILE_PHOTO_CONFLICT,
        AuthErrorCode.PROFILE_UPDATE_FAILED,
    )
)


@router.put(
    "/me/photo",
    response_model=UserResponse,
    responses=PHOTO_ERRORS,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def upload_profile_photo(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfilePhotoService = Depends(),
) -> UserResponse:
    return await service.upload(current_user.id, request.stream())


@router.get(
    "/me/photo",
    response_class=Response,
    responses={
        **PHOTO_ERRORS,
        200: {"content": {"image/webp": {"schema": {"type": "string", "format": "binary"}}}},
    },
)
async def read_profile_photo(
    version: str | None = Query(default=None, max_length=32),
    current_user: UserResponse = Depends(get_current_user),
    service: ProfilePhotoService = Depends(),
) -> Response:
    data = await service.read(current_user.id, version)
    return Response(
        data,
        media_type="image/webp",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/me/photo", response_model=UserResponse, responses=PHOTO_ERRORS)
async def delete_profile_photo(
    current_user: UserResponse = Depends(get_current_user), service: ProfilePhotoService = Depends()
) -> UserResponse:
    return await service.delete(current_user.id)


@router.post(
    "/me/deletion-code",
    response_model=DeleteAccountCodeResponse,
    responses=auth_error_responses(
        AuthErrorCode.INVALID_TOKEN,
        AuthErrorCode.USER_NOT_FOUND,
        AuthErrorCode.INSUFFICIENT_ROLE,
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.EMAIL_DISABLED,
        AuthErrorCode.ACCOUNT_DELETE_CODE_THROTTLED,
        AuthErrorCode.ACCOUNT_DELETE_CODE_SEND_FAILED,
    ),
)
async def request_deletion_code(
    request: Request,
    current_user: UserResponse = Depends(get_current_session_user),
    service: AuthService = Depends(AuthService),
) -> DeleteAccountCodeResponse:
    await service.request_account_deletion_code(
        current_user.id, _resolve_preferred_language(request)
    )
    return DeleteAccountCodeResponse(expires_in=600, retry_after=30)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=auth_error_responses(
        AuthErrorCode.INVALID_TOKEN,
        AuthErrorCode.USER_NOT_FOUND,
        AuthErrorCode.INSUFFICIENT_ROLE,
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.ACCOUNT_DELETE_FAILED,
        AuthErrorCode.ACCOUNT_BILLING_REVIEW_REQUIRED,
        AuthErrorCode.EMAIL_DISABLED,
        AuthErrorCode.ACCOUNT_DELETE_CODE_INVALID,
        AuthErrorCode.ACCOUNT_DELETE_CONFIRMATION_REQUIRED,
        AuthErrorCode.LAST_ADMIN_REQUIRED,
    ),
    description="Permanently deletes the current account, credentials, OAuth identities and API keys. Requires bearer authentication, matching email confirmation and a single-use emailed code. Clears refresh cookies; all sessions stop authenticating.",
)
async def delete_me(
    form: DeleteAccountForm,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_session_user),
    service: AuthService = Depends(AuthService),
) -> None:
    await service.delete_account(
        current_user.id, form.email, form.code, request.headers.get("accept-language")
    )
    clear_refresh_cookies(response)


@router.post(
    "/logout",
    description="Invalidates all refresh sessions for the authenticated user and expires both "
    "refresh cookies. Already-issued access tokens remain valid until their expiry.",
    responses={
        **current_user_error_responses(),
        status.HTTP_200_OK: {
            "headers": {
                "Set-Cookie": {
                    "description": "Separate expiry headers for template_refresh_token and "
                    "template_refresh_sid at Path=/.",
                    "schema": {"type": "string"},
                }
            },
        },
    },
)
async def logout(
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    service: AuthService = Depends(AuthService),
) -> dict[str, str]:
    await service.logout(current_user.id)
    clear_refresh_cookies(response)
    return {"message": "Successfully logged out."}


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    description="Refreshes the access token and extends the existing refresh session TTL. "
    "The refresh token value is retained. Non-empty JSON fields take precedence over cookies; "
    "user_id can be resolved from the session. Browser clients may send an empty JSON object.",
    openapi_extra={
        "parameters": [
            {
                "name": "template_refresh_token",
                "in": "cookie",
                "required": False,
                "schema": {"type": "string"},
            },
            {
                "name": "template_refresh_sid",
                "in": "cookie",
                "required": False,
                "schema": {"type": "string"},
            },
        ]
    },
    responses={
        status.HTTP_200_OK: {"headers": REFRESH_COOKIE_HEADERS},
        **auth_error_responses(
            AuthErrorCode.LOGIN_DISABLED,
            AuthErrorCode.INVALID_TOKEN,
            AuthErrorCode.USER_NOT_FOUND,
        ),
    },
)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Body(default=None, embed=True),
    user_id: int | None = Body(default=None, embed=True),
    session_id: str | None = Body(default=None, embed=True),
    service: AuthService = Depends(AuthService),
) -> RefreshResponse:
    try:
        token_payload, session_id_value, remember_me = await service.refresh_with_request_context(
            request=request,
            refresh_token=refresh_token,
            user_id=user_id,
            session_id=session_id,
        )
    except AuthException:
        clear_refresh_cookies(response)
        raise

    set_refresh_cookies(
        response=response,
        request=request,
        refresh_token=token_payload.refresh_token,
        refresh_session_id=session_id_value,
        remember_me=remember_me,
    )
    return token_payload


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    responses=auth_error_responses(
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.EMAIL_DISABLED,
        AuthErrorCode.INVALID_TOKEN,
        AuthErrorCode.USER_NOT_FOUND,
    ),
)
async def verify_email(
    request: Request,
    form: VerifyEmailForm,
    service: AuthService = Depends(AuthService),
) -> VerifyEmailResponse:
    user = await service.verify_email(
        form.token, preferred_language=_resolve_preferred_language(request)
    )
    return VerifyEmailResponse(message="Email verified successfully.", user=user)


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    responses=auth_error_responses(AuthErrorCode.LOGIN_DISABLED),
)
async def resend_verification_email(
    request: Request,
    form: ResendVerificationForm,
    service: AuthService = Depends(AuthService),
) -> ResendVerificationResponse:
    await service.resend_verification_email(
        form.email,
        preferred_language=_resolve_preferred_language(request),
    )
    return ResendVerificationResponse(
        message="If an unverified account exists, a verification email has been sent.",
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    responses=auth_error_responses(
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.EMAIL_DISABLED,
    ),
)
async def forgot_password(
    request: Request,
    form: ForgotPasswordForm,
    service: AuthService = Depends(AuthService),
) -> ForgotPasswordResponse:
    await service.request_password_reset(
        form.email,
        preferred_language=_resolve_preferred_language(request),
    )
    return ForgotPasswordResponse(
        message="If the account exists, a password reset email has been sent.",
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    responses=auth_error_responses(
        AuthErrorCode.LOGIN_DISABLED,
        AuthErrorCode.INVALID_TOKEN,
        AuthErrorCode.EMAIL_DISABLED,
        AuthErrorCode.USER_NOT_FOUND,
    ),
)
async def reset_password(
    form: ResetPasswordForm,
    service: AuthService = Depends(AuthService),
) -> ResetPasswordResponse:
    await service.reset_password(form.token, form.password)
    return ResetPasswordResponse(message="Password reset completed successfully.")
