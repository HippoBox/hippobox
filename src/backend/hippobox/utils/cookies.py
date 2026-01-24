from datetime import timedelta

from fastapi import Request, Response
from hippobox.core.settings import SETTINGS

REFRESH_COOKIE_NAME = "hippobox_refresh_token"
REFRESH_UID_COOKIE_NAME = "hippobox_refresh_uid"


def get_refresh_cookie_value(request: Request) -> tuple[str | None, str | None]:
    return (
        request.cookies.get(REFRESH_COOKIE_NAME),
        request.cookies.get(REFRESH_UID_COOKIE_NAME),
    )


def set_refresh_cookies(
    response: Response,
    request: Request,
    refresh_token: str,
    user_id: int,
    remember_me: bool = True,
) -> None:
    secure = request.url.scheme == "https"
    cookie_params = {
        "httponly": True,
        "secure": secure,
        "samesite": "none" if secure else "lax",
        "path": "/",
    }

    if remember_me:
        expire_days = getattr(SETTINGS, "REFRESH_TOKEN_EXPIRE_DAYS", 7)
        max_age = int(timedelta(days=expire_days).total_seconds())
        cookie_params["max_age"] = max_age

    response.set_cookie(REFRESH_COOKIE_NAME, refresh_token, **cookie_params)
    response.set_cookie(REFRESH_UID_COOKIE_NAME, str(user_id), **cookie_params)


def clear_refresh_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_UID_COOKIE_NAME, path="/")
