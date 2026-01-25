import asyncio
import logging
import re

from hippobox.core.settings import SETTINGS
from hippobox.core.validation import EMAIL_REGEX, NAME_REGEX, is_password_strong
from hippobox.errors.auth import AuthException
from hippobox.models.auth import Auths
from hippobox.models.credential import Credentials
from hippobox.models.user import UserRole, Users
from hippobox.utils.security import get_password_hash

log = logging.getLogger("bootstrap")


class AdminBootstrapError(ValueError):
    pass


def _validate_admin_inputs(email: str, password: str, name: str):
    if not email:
        raise AdminBootstrapError("ADMIN_EMAIL is required")
    if not re.match(EMAIL_REGEX, email):
        raise AdminBootstrapError("ADMIN_EMAIL is not a valid email address")

    if not name:
        raise AdminBootstrapError("ADMIN_NAME is required")
    if not re.match(NAME_REGEX, name):
        raise AdminBootstrapError("ADMIN_NAME does not match the naming rules")

    if not password:
        raise AdminBootstrapError("ADMIN_PASSWORD is required")
    if not is_password_strong(password):
        raise AdminBootstrapError("ADMIN_PASSWORD is too weak (uppercase+digit+symbol, 8-64 chars, no spaces)")


async def _hash_password(password: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_password_hash, password)


async def bootstrap_admin_user(
    email: str,
    password: str,
    name: str,
    *,
    verify_email: bool = True,
) -> bool:
    if await Users.admin_exists():
        log.info("Admin user already exists. Skipping bootstrap.")
        return False

    if not email or not password or not name:
        raise AdminBootstrapError("Admin bootstrap skipped: missing required inputs")

    _validate_admin_inputs(email, password, name)

    hashed_password = await _hash_password(password)
    try:
        user = await Users.create_with_role(
            {"email": email, "name": name},
            role=UserRole.ADMIN,
            is_verified=verify_email,
        )
    except AuthException as exc:
        raise AdminBootstrapError(exc.message) from exc

    await Credentials.create(user.id, hashed_password)
    await Auths.create(user.id, "email", email)

    log.info("Admin user created: %s", email)
    return True


async def ensure_default_admin_from_settings() -> bool:
    if not SETTINGS.ADMIN_BOOTSTRAP:
        return False

    try:
        return await bootstrap_admin_user(
            SETTINGS.ADMIN_EMAIL,
            SETTINGS.ADMIN_PASSWORD,
            SETTINGS.ADMIN_NAME,
            verify_email=SETTINGS.ADMIN_VERIFY_EMAIL,
        )
    except (AdminBootstrapError, Exception) as exc:
        log.warning("Admin bootstrap failed: %s", exc)
        return False


async def ensure_admin_for_login_disabled() -> bool:
    if SETTINGS.LOGIN_ENABLED:
        return False
    if await Users.admin_exists():
        return False

    email = SETTINGS.ADMIN_EMAIL or "admin@local.test"
    password = SETTINGS.ADMIN_PASSWORD or "Admin123!"
    name = SETTINGS.ADMIN_NAME or "admin"

    if not SETTINGS.ADMIN_EMAIL or not SETTINGS.ADMIN_PASSWORD:
        log.warning(
            "LOGIN_ENABLED is false and no admin credentials provided. "
            "Auto-creating admin with defaults (email=%s). Set ADMIN_EMAIL/ADMIN_PASSWORD.",
            email,
        )

    try:
        return await bootstrap_admin_user(
            email,
            password,
            name,
            verify_email=True,
        )
    except (AdminBootstrapError, Exception) as exc:
        log.warning("Auto admin bootstrap failed: %s", exc)
        return False
