"""Development-only identity provisioning; never promote an existing normal account."""

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.error import AuthException
from hippobox.platform.models.user import UserResponse, UserRole, Users


class BootstrapService:
    async def initialize(self) -> UserResponse:
        if SETTINGS.APP_MODE != "development" or SETTINGS.LOGIN_ENABLED:
            raise ValueError("Bootstrap requires development mode with login disabled.")
        email = SETTINGS.BOOTSTRAP_USER_EMAIL.strip().lower()
        name = SETTINGS.BOOTSTRAP_USER_NAME.strip()
        if not email or not name:
            raise ValueError("Bootstrap email and name are required.")
        user = await Users.get_user_response_by_email(email)
        if user is None:
            try:
                await Users.create_oauth_user(
                    email=email,
                    name=name,
                    provider="bootstrap",
                    identifier=email,
                    is_verified=True,
                    role=UserRole.ADMIN,
                )
            except AuthException:
                # Another process may have provisioned the identity. Validate it below.
                pass
            user = await Users.get_user_response_by_email(email)
        identity = await Users.get_auth_user_by_identity("bootstrap", email)
        if (
            user is None
            or identity is None
            or identity.id != user.id
            or identity.password_hash is not None
            or identity.role != UserRole.ADMIN
        ):
            raise ValueError(
                "Bootstrap identity conflict: use a dedicated active development admin account."
            )
        return user
