from urllib.parse import urlencode

from hippobox.core.settings import SETTINGS

EMAIL_VERIFY_SUCCESS_PATH = "/verify-email/success"
EMAIL_VERIFY_FAILURE_PATH = "/verify-email/failure"
PASSWORD_RESET_PATH = "/reset-password"


def _join_base(base: str, path: str) -> str:
    if not base:
        return path
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def build_verify_email_link(token: str) -> str:
    api_base = SETTINGS.PUBLIC_API_URL
    path = f"/api/v1/auth/verify-email/{token}"
    link = _join_base(api_base, path)

    if SETTINGS.PUBLIC_APP_URL:
        return f"{link}?{urlencode({'redirect': '1'})}"
    return link


def build_verify_email_redirect_url(success: bool) -> str:
    app_base = SETTINGS.PUBLIC_APP_URL
    path = EMAIL_VERIFY_SUCCESS_PATH if success else EMAIL_VERIFY_FAILURE_PATH
    return _join_base(app_base, path)


def build_password_reset_link(token: str) -> str:
    app_base = SETTINGS.PUBLIC_APP_URL
    path = PASSWORD_RESET_PATH
    link = _join_base(app_base, path)
    return f"{link}?{urlencode({'token': token})}"
