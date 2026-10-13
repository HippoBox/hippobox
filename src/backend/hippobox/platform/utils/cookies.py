import hashlib
from datetime import timedelta

from fastapi import Request, Response

from hippobox.platform.core.config.settings import SETTINGS

REFRESH_COOKIE_NAME = "hippobox_refresh_token"
REFRESH_SID_COOKIE_NAME = "hippobox_refresh_sid"


def refresh_cookie_names() -> tuple[str, str]:
    # Root keeps existing names. Prefix-specific names also avoid collisions with a root app.
    suffix = (
        "_" + hashlib.sha256(SETTINGS.APP_BASE_PATH.encode()).hexdigest()[:16]
        if SETTINGS.APP_BASE_PATH
        else ""
    )
    return REFRESH_COOKIE_NAME + suffix, REFRESH_SID_COOKIE_NAME + suffix


def _is_https_request(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto:
        first_proto = forwarded_proto.split(",")[0].strip().lower()
        if first_proto == "https":
            return True
    return request.url.scheme == "https"


def get_refresh_cookie_value(request: Request) -> tuple[str | None, str | None]:
    token_name, sid_name = refresh_cookie_names()
    return request.cookies.get(token_name), request.cookies.get(sid_name)


def set_refresh_cookies(
    response: Response,
    request: Request,
    refresh_token: str,
    refresh_session_id: str,
    remember_me: bool = True,
) -> None:
    secure = _is_https_request(request)
    cookie_params = {
        "httponly": True,
        "secure": secure,
        "samesite": "none" if secure else "lax",
        "path": SETTINGS.APP_BASE_PATH + "/",
    }

    if remember_me:
        ttl_seconds = int(timedelta(days=SETTINGS.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
        cookie_params["max_age"] = ttl_seconds
        cookie_params["expires"] = ttl_seconds

    token_name, sid_name = refresh_cookie_names()
    response.set_cookie(token_name, refresh_token, **cookie_params)
    response.set_cookie(sid_name, refresh_session_id, **cookie_params)


def clear_refresh_cookies(response: Response) -> None:
    for name in refresh_cookie_names():
        response.delete_cookie(name, path=SETTINGS.APP_BASE_PATH + "/")
