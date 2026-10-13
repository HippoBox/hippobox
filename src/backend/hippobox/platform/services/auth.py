import asyncio
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request as URLRequest, urlopen

from fastapi import Depends, Request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from hippobox.platform.core.cache.redis import RedisManager
from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.error import AuthErrorCode, AuthException
from hippobox.platform.core.mail.queue import MAIL_QUEUE_SERVICE
from hippobox.platform.core.observability.logging import get_logger, mask_email
from hippobox.platform.core.observability.service import observe_service
from hippobox.platform.models.oauth import (
    OAuthIdentityProfile,
    OAuthProvider,
    OAuthProviderConfig,
    OAuthProviderPublicConfig,
)
from hippobox.platform.models.user import (
    AdminUserListResponse,
    ChangePasswordForm,
    LoginForm,
    LoginResponse,
    RefreshResponse,
    SignupForm,
    UpdateProfileForm,
    UserResponse,
    UserRole,
    UserRoleStatsResponse,
    Users,
)
from hippobox.platform.services.profile_photo import ProfilePhotoService
from hippobox.platform.utils.account_verification import (
    consume_deletion_code,
    consume_email_code,
    issue_deletion_code,
    issue_email_code,
)
from hippobox.platform.utils.cookies import get_refresh_cookie_value
from hippobox.platform.utils.security import hash_password, verify_password
from hippobox.platform.utils.token import (
    consume_email_verification_token,
    consume_password_reset_token,
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    delete_account_tokens,
    delete_refresh_token,
    get_refresh_session,
    store_email_verification_token,
    store_password_reset_token,
    store_refresh_token,
    verify_refresh_token,
)

logger = get_logger("hippobox.platform.service.auth")
EMAIL_LANGUAGE_BY_PREFIX = {
    "en": "en",
    "ko": "ko",
}


class AuthService:
    def __init__(self, photos: ProfilePhotoService = Depends(ProfilePhotoService)):
        self.photos = photos

    def _ensure_login_enabled(self) -> None:
        if not SETTINGS.LOGIN_ENABLED:
            logger.debug("Blocked request because login is disabled.")
            raise AuthException(code=AuthErrorCode.LOGIN_DISABLED)

    def get_oauth_provider_configs(self) -> list[OAuthProviderConfig]:
        self._ensure_login_enabled()
        if not SETTINGS.OAUTH_ENABLED:
            return []

        validation_errors = SETTINGS.get_oauth_validation_errors()
        if validation_errors:
            raise AuthException(
                code=AuthErrorCode.OAUTH_PROVIDER_CONFIG_INVALID,
                details={"errors": validation_errors},
            )

        provider_configs = SETTINGS.get_oauth_provider_configs()
        return [
            OAuthProviderConfig(
                provider=OAuthProvider(provider),
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                authorize_url=config["authorize_url"],
                token_url=config["token_url"],
                userinfo_url=config["userinfo_url"],
            )
            for provider, config in provider_configs.items()
        ]

    def get_oauth_provider_public_configs(self) -> list[OAuthProviderPublicConfig]:
        return [
            OAuthProviderPublicConfig(
                provider=config.provider,
                start_path=f"/api/v1/auth/oauth/{config.provider}/start",
            )
            for config in self.get_oauth_provider_configs()
        ]

    async def get_admin_user_role_stats(self) -> UserRoleStatsResponse:
        stats = await Users.get_user_role_stats()
        return UserRoleStatsResponse(**stats)

    @observe_service("auth.admin_users")
    async def list_admin_users(
        self,
        *,
        page: int,
        page_size: int,
        search: str,
        role: UserRole | None,
        is_active: bool | None,
    ) -> AdminUserListResponse:
        try:
            return await Users.list_admin_users(
                page=page,
                page_size=page_size,
                search=search.strip(),
                role=role,
                is_active=is_active,
            )
        except SQLAlchemyError as error:
            raise AuthException(code=AuthErrorCode.ADMIN_USERS_FAILED) from error

    async def create_oauth_state(self, provider: OAuthProvider) -> str:
        state = create_refresh_token()
        redis = await RedisManager.get_client()
        await redis.setex(
            f"oauth_state:{state}",
            timedelta(minutes=SETTINGS.OAUTH_STATE_EXPIRE_MINUTES),
            provider.value,
        )
        logger.debug("OAuth state created (provider=%s).", provider.value)
        return state

    async def consume_oauth_state(self, state: str) -> OAuthProvider | None:
        redis = await RedisManager.get_client()
        key = f"oauth_state:{state}"
        provider_value = await redis.get(key)
        if provider_value is None:
            return None
        await redis.delete(key)
        try:
            logger.debug("OAuth state consumed (provider=%s).", provider_value)
            return OAuthProvider(provider_value)
        except ValueError:
            logger.debug("OAuth state consumed with unsupported provider value.")
            return None

    async def build_oauth_authorization_url(
        self,
        provider: OAuthProvider,
        redirect_uri: str,
    ) -> str:
        provider_config = self._get_oauth_provider_config(provider)
        state = await self.create_oauth_state(provider)

        if provider == OAuthProvider.GOOGLE:
            query = {
                "response_type": "code",
                "client_id": provider_config.client_id,
                "redirect_uri": redirect_uri,
                "scope": "openid email profile",
                "state": state,
                "access_type": "online",
                "prompt": "select_account",
            }
        else:
            query = {
                "client_id": provider_config.client_id,
                "redirect_uri": redirect_uri,
                "scope": "read:user user:email",
                "state": state,
            }

        return f"{provider_config.authorize_url}?{urlencode(query)}"

    async def oauth_callback_login(
        self,
        provider: OAuthProvider,
        code: str,
        state: str,
        redirect_uri: str,
        request: Request,
        refresh_session_id: str,
    ) -> LoginResponse:
        provider_config = self._get_oauth_provider_config(provider)
        consumed_provider = await self.consume_oauth_state(state)
        if consumed_provider is None or consumed_provider != provider:
            logger.debug(
                "OAuth callback rejected due to invalid state (provider=%s).", provider.value
            )
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message="Invalid OAuth state.",
            )

        access_token = await self._exchange_oauth_code(
            provider=provider,
            provider_config=provider_config,
            code=code,
            redirect_uri=redirect_uri,
        )
        profile = await self._fetch_oauth_profile(provider, provider_config, access_token)

        user = await self._resolve_oauth_user(profile, request.headers.get("accept-language"))
        user_ip = self._get_client_ip(request)
        await Users.update_login_metadata(
            user_id=user.id,
            provider=provider.value,
            identifier=profile.provider_user_id,
            login_ip=user_ip,
            user_agent=request.headers.get("user-agent"),
            login_time=datetime.now(UTC),
        )
        logger.info(
            "OAuth login succeeded (provider=%s, user_id=%s, email=%s).",
            provider.value,
            user.id,
            mask_email(user.email),
        )

        issued_access_token, refresh_token = await self._issue_session_tokens(
            user_id=user.id,
            user_email=user.email,
            refresh_session_id=refresh_session_id,
            remember_me=True,
        )
        return LoginResponse(
            access_token=issued_access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user.as_user_response(),
        )

    def require_oauth_callback_params(
        self,
        *,
        provider: OAuthProvider,
        code: str | None,
        state: str | None,
    ) -> tuple[str, str]:
        if not code or not state:
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message=f"OAuth callback requires code and state (provider={provider.value}).",
            )
        return code, state

    async def request_account_deletion_code(
        self, user_id: int, preferred_language: str | None = None
    ) -> None:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            raise AuthException(code=AuthErrorCode.EMAIL_DISABLED)
        user = await Users.get_user_response_by_id(user_id)
        if user is None:
            raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)
        try:
            code, retry_after = await issue_deletion_code(
                user_id,
                ttl=600,
                cooldown=30,
                request_limit=5,
                request_window=3600,
            )
            if code is None:
                raise AuthException(
                    code=AuthErrorCode.ACCOUNT_DELETE_CODE_THROTTLED,
                    details={"remaining_seconds": retry_after},
                )
            await MAIL_QUEUE_SERVICE.enqueue_account_deletion(
                to_email=user.email,
                user_name=user.name,
                code=code,
                language=self._resolve_email_language(preferred_language),
            )
        except AuthException:
            raise
        except Exception as error:
            raise AuthException(code=AuthErrorCode.ACCOUNT_DELETE_CODE_SEND_FAILED) from error

    async def delete_account(
        self, user_id: int, email: str, code: str, preferred_language: str | None = None
    ) -> None:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            raise AuthException(code=AuthErrorCode.EMAIL_DISABLED)
        try:
            user = await Users.get_user_response_by_id(user_id)
            if user is None:
                raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)
            if user.email.casefold() != email.strip().casefold():
                raise AuthException(code=AuthErrorCode.ACCOUNT_DELETE_CONFIRMATION_REQUIRED)
            if not await consume_deletion_code(user_id, code, attempt_limit=5, window=600):
                raise AuthException(code=AuthErrorCode.ACCOUNT_DELETE_CODE_INVALID)
            from hippobox.platform.services.notifications import notification_row

            notice = notification_row(
                f"account-deleted:{user_id}",
                "account_deleted",
                email=user.email,
                name=user.name,
                language=self._resolve_email_language(preferred_language),
            )
            deleted_photo = await Users.delete_account(user_id, email, notification=notice)
        except AuthException:
            raise
        except Exception as error:
            raise AuthException(code=AuthErrorCode.ACCOUNT_DELETE_FAILED) from error
        if deleted_photo:
            await self.photos.cleanup(deleted_photo)
        try:
            await delete_account_tokens(user_id)
        except Exception:
            # The deleted DB principal rejects access/refresh/one-time tokens even
            # while Redis is unavailable; orphaned entries retain their normal TTL.
            logger.exception("Deleted account token cleanup failed (user_id=%s).", user_id)
        from hippobox.platform.services.notifications import wake_notifications

        await wake_notifications()
        logger.info("Account deleted (user_id=%s).", user_id)

    async def signup(self, form: SignupForm, preferred_language: str | None = None) -> UserResponse:
        self._ensure_login_enabled()
        logger.info("Signup attempt (email=%s).", mask_email(form.email))
        try:
            user = await Users.create_signup_user(
                email=form.email,
                name=form.name,
                password_hash=hash_password(form.password),
                is_verified=not SETTINGS.EMAIL_ENABLED,
            )
        except IntegrityError as error:
            logger.debug("Signup failed due to integrity error (email=%s).", mask_email(form.email))
            message = str(error.orig)
            if "user.name" in message or 'constraint "user_name_key"' in message:
                raise AuthException(code=AuthErrorCode.NAME_ALREADY_EXISTS) from error
            if "user.email" in message or 'constraint "user_email_key"' in message:
                raise AuthException(code=AuthErrorCode.EMAIL_ALREADY_EXISTS) from error
            raise AuthException(code=AuthErrorCode.SIGNUP_FAILED) from error

        except AuthException:
            raise
        except Exception as error:
            logger.exception("Signup persistence failed.")
            raise AuthException(code=AuthErrorCode.SIGNUP_FAILED) from error

        if SETTINGS.EMAIL_ENABLED:
            language = self._resolve_email_language(preferred_language)
            await self._send_verification_email(user.id, user.email, user.name, language)
        logger.info("Signup completed (user_id=%s, verified=%s).", user.id, user.is_verified)
        return user

    async def login(
        self, form: LoginForm, request: Request, refresh_session_id: str
    ) -> LoginResponse:
        self._ensure_login_enabled()
        user_ip = self._get_client_ip(request)
        logger.debug("Login attempt received (email=%s, ip=%s).", mask_email(form.email), user_ip)
        await self._check_login_limit(user_ip)

        user = await Users.get_auth_user_by_email(form.email)

        if user is None or not user.password_hash:
            remaining_attempts = await self._register_login_failure(user_ip)
            logger.debug(
                "Login failed: invalid credentials (email=%s, ip=%s, remaining_attempts=%s).",
                mask_email(form.email),
                user_ip,
                remaining_attempts,
            )
            raise AuthException(
                code=AuthErrorCode.INVALID_CREDENTIALS,
                details={"remaining_attempts": remaining_attempts},
            )

        if not verify_password(form.password, user.password_hash):
            remaining_attempts = await self._register_login_failure(user_ip)
            logger.debug(
                "Login failed: invalid password (email=%s, ip=%s, remaining_attempts=%s).",
                mask_email(form.email),
                user_ip,
                remaining_attempts,
            )
            raise AuthException(
                code=AuthErrorCode.INVALID_CREDENTIALS,
                details={"remaining_attempts": remaining_attempts},
            )

        if SETTINGS.EMAIL_ENABLED and not user.is_verified:
            logger.debug("Login blocked: email not verified (user_id=%s).", user.id)
            raise AuthException(code=AuthErrorCode.EMAIL_NOT_VERIFIED)

        await self._reset_login_fail_count(user_ip)
        await Users.update_login_metadata(
            user_id=user.id,
            provider="email",
            identifier=user.email,
            login_ip=user_ip,
            user_agent=request.headers.get("user-agent"),
            login_time=datetime.now(UTC),
        )
        logger.info("Login succeeded (user_id=%s, ip=%s).", user.id, user_ip)

        access_token, refresh_token = await self._issue_session_tokens(
            user_id=user.id,
            user_email=user.email,
            refresh_session_id=refresh_session_id,
            remember_me=form.remember_me,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user.as_user_response(),
        )

    async def logout(self, user_id: int) -> None:
        await delete_refresh_token(user_id)
        logger.info("Logout completed (user_id=%s).", user_id)

    async def refresh_access_token(
        self,
        user_id: int,
        refresh_session_id: str,
        refresh_token: str,
        remember_me: bool = False,
    ) -> RefreshResponse:
        self._ensure_login_enabled()
        is_valid = await verify_refresh_token(user_id, refresh_session_id, refresh_token)
        if not is_valid:
            logger.debug("Refresh rejected: invalid token (user_id=%s).", user_id)
            raise AuthException(code=AuthErrorCode.INVALID_TOKEN)

        user = await Users.get_auth_user_by_id(user_id)
        if user is None:
            logger.debug("Refresh rejected: user not found (user_id=%s).", user_id)
            raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)

        access_token = create_access_token(
            subject=str(user.id),
            email=user.email,
            expires_delta=timedelta(minutes=SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        await store_refresh_token(
            user.id,
            refresh_session_id,
            refresh_token,
            remember_me=remember_me,
        )
        logger.debug("Refresh token rotated (user_id=%s, remember_me=%s).", user_id, remember_me)

        return RefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def refresh_with_request_context(
        self,
        *,
        request: Request,
        refresh_token: str | None,
        user_id: int | None,
        session_id: str | None,
    ) -> tuple[RefreshResponse, str, bool]:
        self._ensure_login_enabled()
        cookie_token, cookie_session_id = get_refresh_cookie_value(request)
        refresh_token_value = refresh_token or cookie_token
        session_id_value = session_id or cookie_session_id
        user_id_value = user_id
        remember_me = False

        if session_id_value:
            session = await get_refresh_session(session_id_value)
            if session is not None:
                session_user_id, session_remember_me = session
                remember_me = session_remember_me
                if user_id_value is None:
                    user_id_value = session_user_id

        if not refresh_token_value or not session_id_value or user_id_value is None:
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message="Refresh token, session_id, and user_id are required.",
            )

        try:
            token_payload = await self.refresh_access_token(
                user_id=int(user_id_value),
                refresh_session_id=session_id_value,
                refresh_token=refresh_token_value,
                remember_me=remember_me,
            )
        except ValueError as error:
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message="Invalid refresh token payload.",
            ) from error

        return token_payload, session_id_value, remember_me

    async def _issue_session_tokens(
        self,
        user_id: int,
        user_email: str,
        refresh_session_id: str,
        remember_me: bool = False,
    ) -> tuple[str, str]:
        access_token = create_access_token(
            subject=str(user_id),
            email=user_email,
            expires_delta=timedelta(minutes=SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token()
        await store_refresh_token(
            user_id,
            refresh_session_id,
            refresh_token,
            remember_me=remember_me,
        )
        return access_token, refresh_token

    def _get_oauth_provider_config(self, provider: OAuthProvider) -> OAuthProviderConfig:
        provider_configs = {config.provider: config for config in self.get_oauth_provider_configs()}
        if provider not in provider_configs:
            raise AuthException(
                code=AuthErrorCode.OAUTH_PROVIDER_NOT_ENABLED,
                details={"provider": provider.value},
            )
        return provider_configs[provider]

    async def _exchange_oauth_code(
        self,
        provider: OAuthProvider,
        provider_config: OAuthProviderConfig,
        code: str,
        redirect_uri: str,
    ) -> str:
        data = {
            "code": code,
            "client_id": provider_config.client_id,
            "client_secret": provider_config.client_secret,
            "redirect_uri": redirect_uri,
        }
        if provider == OAuthProvider.GOOGLE:
            data["grant_type"] = "authorization_code"

        body = urlencode(data).encode("utf-8")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        payload = await self._http_request_json(
            method="POST",
            url=provider_config.token_url,
            headers=headers,
            body=body,
        )
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message="OAuth token exchange failed.",
            )
        return token

    async def _fetch_oauth_profile(
        self,
        provider: OAuthProvider,
        provider_config: OAuthProviderConfig,
        access_token: str,
    ) -> OAuthIdentityProfile:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        payload = await self._http_request_json(
            method="GET",
            url=provider_config.userinfo_url,
            headers=headers,
        )

        if provider == OAuthProvider.GOOGLE:
            provider_user_id = str(payload.get("sub", "")).strip()
            email = str(payload.get("email", "")).strip().lower()
            name = str(payload.get("name", "")).strip() or email
            email_verified = bool(payload.get("email_verified", False))
        else:
            provider_user_id = str(payload.get("id", "")).strip()
            email = str(payload.get("email", "")).strip().lower()
            name = str(payload.get("name", "")).strip() or str(payload.get("login", "")).strip()
            verified_email, email_verified = await self._fetch_github_primary_email(
                provider_config,
                access_token,
            )
            if verified_email:
                email = verified_email

        if not provider_user_id or not email:
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message="OAuth profile payload is incomplete.",
            )

        return OAuthIdentityProfile(
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            name=name or email,
            email_verified=email_verified,
        )

    async def _fetch_github_primary_email(
        self,
        provider_config: OAuthProviderConfig,
        access_token: str,
    ) -> tuple[str, bool]:
        emails_url = provider_config.userinfo_url.rstrip("/") + "/emails"
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        payload = await self._http_request_json(method="GET", url=emails_url, headers=headers)
        if not isinstance(payload, list):
            return "", False
        for item in payload:
            if not isinstance(item, Mapping):
                continue
            if item.get("primary") and item.get("verified") and item.get("email"):
                return str(item["email"]).strip().lower(), True
        for item in payload:
            if isinstance(item, Mapping) and item.get("verified") and item.get("email"):
                return str(item["email"]).strip().lower(), True
        return "", False

    async def _resolve_oauth_user(
        self, profile: OAuthIdentityProfile, preferred_language: str | None = None
    ):
        if not profile.email_verified:
            logger.debug(
                "OAuth profile rejected: unverified email (provider=%s).", profile.provider.value
            )
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message="OAuth email is not verified.",
            )

        auth_user = await Users.get_auth_user_by_identity(
            provider=profile.provider.value,
            identifier=profile.provider_user_id,
        )
        if auth_user is not None:
            logger.debug("OAuth identity matched existing user (user_id=%s).", auth_user.id)
            return auth_user

        existing_user = await Users.get_user_response_by_email(profile.email)
        if existing_user is not None:
            linked = await Users.link_auth_identity(
                user_id=existing_user.id,
                provider=profile.provider.value,
                identifier=profile.provider_user_id,
            )
            if not linked:
                logger.debug(
                    "OAuth identity conflict (provider=%s, email=%s).",
                    profile.provider.value,
                    mask_email(profile.email),
                )
                raise AuthException(
                    code=AuthErrorCode.OAUTH_IDENTITY_CONFLICT,
                )
            linked_user = await Users.get_auth_user_by_id(existing_user.id)
            if linked_user is None:
                raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)
            logger.info(
                "OAuth identity linked to existing user (provider=%s, user_id=%s).",
                profile.provider.value,
                existing_user.id,
            )
            return linked_user

        try:
            await Users.create_oauth_user(
                email=profile.email,
                name=profile.name,
                provider=profile.provider.value,
                identifier=profile.provider_user_id,
                is_verified=profile.email_verified,
            )
        except IntegrityError as error:
            logger.debug(
                "OAuth signup failed due to integrity error (provider=%s, email=%s).",
                profile.provider.value,
                mask_email(profile.email),
            )
            raise AuthException(
                code=AuthErrorCode.OAUTH_SIGNUP_FAILED,
            ) from error

        created_user = await Users.get_auth_user_by_identity(
            provider=profile.provider.value,
            identifier=profile.provider_user_id,
        )
        if created_user is None:
            raise AuthException(code=AuthErrorCode.OAUTH_SIGNUP_FAILED)
        logger.info(
            "OAuth user created (provider=%s, user_id=%s).", profile.provider.value, created_user.id
        )
        await self._send_welcome_email(created_user, preferred_language)
        return created_user

    async def _http_request_json(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ):
        def _do_request():
            request = URLRequest(url=url, data=body, method=method)
            for key, value in (headers or {}).items():
                request.add_header(key, value)
            with urlopen(request, timeout=10) as response:
                return response.read().decode("utf-8")

        try:
            raw = await asyncio.to_thread(_do_request)
            payload = json.loads(raw)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
            logger.debug("OAuth provider request failed (method=%s, url=%s).", method, url)
            raise AuthException(
                code=AuthErrorCode.OAUTH_PROVIDER_REQUEST_FAILED,
                message="OAuth provider request failed.",
            ) from error

        return payload

    def _get_client_ip(self, request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"
        if not SETTINGS.TRUST_PROXY_HEADERS:
            return client_ip

        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            forwarded_ip = x_forwarded_for.split(",")[0].strip()
            if forwarded_ip:
                return forwarded_ip

        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            real_ip = x_real_ip.strip()
            if real_ip:
                return real_ip

        return client_ip

    async def verify_email(self, token: str, preferred_language: str | None = None) -> UserResponse:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            raise AuthException(code=AuthErrorCode.EMAIL_DISABLED)
        user_id = await consume_email_verification_token(token)
        if user_id is None:
            logger.debug("Email verification failed: token invalid or expired.")
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message="Invalid or expired email verification token.",
            )

        user = await Users.mark_email_verified(user_id)
        if user is None:
            raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)
        await self._send_welcome_email(user, preferred_language)
        logger.info("Email verified (user_id=%s).", user.id)
        return user

    async def resend_verification_email(
        self, email: str, preferred_language: str | None = None
    ) -> None:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            logger.debug("Resend verification skipped because email integration is disabled.")
            return
        user = await Users.get_auth_user_by_email(email)
        if user is None:
            logger.debug(
                "Resend verification skipped: user not found (email=%s).", mask_email(email)
            )
            return
        if user.is_verified:
            logger.debug("Resend verification skipped: already verified (user_id=%s).", user.id)
            return
        language = self._resolve_email_language(preferred_language)
        await self._send_verification_email(user.id, user.email, user.name, language)
        logger.info("Verification email queued (user_id=%s).", user.id)

    async def request_password_reset(
        self, email: str, preferred_language: str | None = None
    ) -> None:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            logger.debug("Password reset rejected because email integration is disabled.")
            raise AuthException(code=AuthErrorCode.EMAIL_DISABLED)

        user = await Users.get_auth_user_by_email(email)
        if user is None:
            logger.debug(
                "Password reset request ignored for unknown email (%s).", mask_email(email)
            )
            return

        language = self._resolve_email_language(preferred_language)
        await self._send_password_reset_email(user.id, user.email, user.name, language)
        logger.info("Password reset email queued (user_id=%s).", user.id)

    async def update_profile(self, user_id: int, form: UpdateProfileForm) -> UserResponse:
        logger.debug("Profile update attempt (user_id=%s).", user_id)
        user = await Users.update_user_profile(
            user_id=user_id,
            name=form.name,
            profile_image_url=form.profile_image_url,
            update_name="name" in form.model_fields_set,
            update_profile_image_url="profile_image_url" in form.model_fields_set,
            keyboard_shortcuts=form.keyboard_shortcuts,
            update_keyboard_shortcuts="keyboard_shortcuts" in form.model_fields_set,
            bio=form.bio,
            location=form.location,
            update_bio="bio" in form.model_fields_set,
            update_location="location" in form.model_fields_set,
        )
        if user is None:
            logger.debug("Profile update failed (user_id=%s).", user_id)
            raise AuthException(code=AuthErrorCode.PROFILE_UPDATE_FAILED)
        logger.info("Profile update completed (user_id=%s).", user_id)
        return user

    async def request_password_change_code(
        self, user_id: int, preferred_language: str | None = None
    ) -> None:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            raise AuthException(code=AuthErrorCode.EMAIL_DISABLED)
        user = await Users.get_auth_user_by_id(user_id)
        if user is None or not user.password_hash:
            raise AuthException(code=AuthErrorCode.INVALID_CREDENTIALS)
        try:
            code, retry_after = await issue_email_code(
                user_id,
                ttl=600,
                cooldown=30,
                request_limit=5,
                request_window=3600,
                purpose="password_change",
            )
            if code is None:
                raise AuthException(
                    code=AuthErrorCode.PASSWORD_CHANGE_CODE_THROTTLED,
                    details={"remaining_seconds": retry_after},
                )
            await MAIL_QUEUE_SERVICE.enqueue_password_change(
                to_email=user.email,
                user_name=user.name,
                code=code,
                language=self._resolve_email_language(preferred_language),
            )
        except AuthException:
            raise
        except Exception as error:
            raise AuthException(code=AuthErrorCode.PASSWORD_CHANGE_CODE_SEND_FAILED) from error

    async def verify_account_email_code(self, user_id: int, code: str, *, password: bool) -> None:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            raise AuthException(code=AuthErrorCode.EMAIL_DISABLED)
        invalid = (
            AuthErrorCode.PASSWORD_CHANGE_CODE_INVALID
            if password
            else AuthErrorCode.ACCOUNT_DELETE_CODE_INVALID
        )
        failed = (
            AuthErrorCode.PASSWORD_CHANGE_FAILED
            if password
            else AuthErrorCode.ACCOUNT_DELETE_FAILED
        )
        try:
            if not await consume_email_code(
                user_id,
                code,
                attempt_limit=5,
                window=600,
                consume=False,
                purpose="password_change" if password else "account_delete",
            ):
                raise AuthException(code=invalid)
        except AuthException:
            raise
        except Exception as error:
            raise AuthException(code=failed) from error

    async def change_password(self, user_id: int, form: ChangePasswordForm) -> None:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            raise AuthException(code=AuthErrorCode.EMAIL_DISABLED)
        try:
            user = await Users.get_auth_user_by_id(user_id)
            if user is None or not user.password_hash:
                raise AuthException(code=AuthErrorCode.INVALID_CREDENTIALS)
            if not await consume_email_code(
                user_id, form.code, attempt_limit=5, window=600, purpose="password_change"
            ):
                raise AuthException(code=AuthErrorCode.PASSWORD_CHANGE_CODE_INVALID)
            # Invalidate renewal before committing the new credential; Redis outages fail closed.
            await delete_refresh_token(user_id)
            if not await Users.change_password_hash(
                user_id, user.password_hash, hash_password(form.password)
            ):
                raise AuthException(code=AuthErrorCode.PASSWORD_CHANGE_CODE_INVALID)
        except AuthException:
            raise
        except Exception as error:
            raise AuthException(code=AuthErrorCode.PASSWORD_CHANGE_FAILED) from error
        logger.info("Password change completed (user_id=%s).", user_id)

    async def reset_password(self, token: str, password: str) -> None:
        self._ensure_login_enabled()
        if not SETTINGS.EMAIL_ENABLED:
            logger.debug("Password reset rejected because email integration is disabled.")
            raise AuthException(code=AuthErrorCode.EMAIL_DISABLED)

        user_id = await consume_password_reset_token(token)
        if user_id is None:
            logger.debug("Password reset failed: token invalid or expired.")
            raise AuthException(
                code=AuthErrorCode.INVALID_TOKEN,
                message="Invalid or expired password reset token.",
            )

        is_updated = await Users.update_password_hash(user_id, hash_password(password))
        if not is_updated:
            raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)

        await delete_refresh_token(user_id)
        logger.info("Password reset completed (user_id=%s).", user_id)

    async def _check_login_limit(self, user_ip: str) -> None:
        redis = await RedisManager.get_client()
        key = f"login_fail:{user_ip}"
        fails = await redis.get(key)

        if fails and int(fails) >= SETTINGS.LOGIN_FAILED_LIMIT:
            remaining_seconds = max(0, await redis.ttl(key))
            logger.debug(
                "Account locked by login-fail limit (ip=%s, remaining_seconds=%s).",
                user_ip,
                remaining_seconds,
            )
            raise AuthException(
                code=AuthErrorCode.ACCOUNT_LOCKED,
                details={"remaining_seconds": remaining_seconds},
            )

    async def _register_login_failure(self, user_ip: str) -> int:
        redis = await RedisManager.get_client()
        key = f"login_fail:{user_ip}"
        count = await redis.incr(key)

        if count == 1:
            await redis.expire(key, timedelta(minutes=SETTINGS.LOGIN_LOCKED_MINUTES))

        remaining_attempts = max(0, SETTINGS.LOGIN_FAILED_LIMIT - count)
        logger.debug(
            "Login failure count incremented (ip=%s, count=%s, remaining_attempts=%s).",
            user_ip,
            count,
            remaining_attempts,
        )

        if remaining_attempts <= 0:
            remaining_seconds = max(0, await redis.ttl(key))
            logger.debug(
                "Account locked after login failures (ip=%s, remaining_seconds=%s).",
                user_ip,
                remaining_seconds,
            )
            raise AuthException(
                code=AuthErrorCode.ACCOUNT_LOCKED,
                details={"remaining_seconds": remaining_seconds},
            )

        return remaining_attempts

    async def _reset_login_fail_count(self, user_ip: str) -> None:
        redis = await RedisManager.get_client()
        await redis.delete(f"login_fail:{user_ip}")

    async def _send_welcome_email(self, user: UserResponse, preferred_language: str | None) -> None:
        try:
            await MAIL_QUEUE_SERVICE.enqueue_welcome(
                to_email=user.email,
                user_name=user.name,
                language=self._resolve_email_language(preferred_language),
            )
        except Exception:
            # A greeting must not turn completed activation/OAuth login into failure.
            logger.exception("Welcome email publication failed (user_id=%s).", user.id)

    async def _send_verification_email(
        self,
        user_id: int,
        email: str,
        name: str,
        language: str,
    ) -> None:
        verification_token = create_email_verification_token()
        await store_email_verification_token(user_id, verification_token)

        verify_path = "/verify-email"
        verify_query = urlencode({"token": verification_token})
        verify_link = urljoin(f"{SETTINGS.APP_BASE_URL.rstrip('/')}/", verify_path.lstrip("/"))
        verify_link = f"{verify_link}?{verify_query}"

        await MAIL_QUEUE_SERVICE.enqueue_signup_verification(
            to_email=email,
            user_name=name,
            link=verify_link,
            language=language,
        )

    async def _send_password_reset_email(
        self,
        user_id: int,
        email: str,
        name: str,
        language: str,
    ) -> None:
        reset_token = create_password_reset_token()
        await store_password_reset_token(user_id, reset_token)

        reset_path = "/reset-password"
        reset_query = urlencode({"token": reset_token})
        reset_link = urljoin(f"{SETTINGS.APP_BASE_URL.rstrip('/')}/", reset_path.lstrip("/"))
        reset_link = f"{reset_link}?{reset_query}"

        await MAIL_QUEUE_SERVICE.enqueue_password_reset(
            to_email=email,
            user_name=name,
            link=reset_link,
            language=language,
        )

    def _resolve_email_language(self, preferred_language: str | None) -> str:
        if not preferred_language:
            return "en"
        primary = preferred_language.split(",")[0].strip().lower()
        normalized = primary.split("-")[0]
        return EMAIL_LANGUAGE_BY_PREFIX.get(normalized, "en")
