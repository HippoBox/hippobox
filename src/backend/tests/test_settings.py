import pytest

from hippobox.core.settings import Settings


def test_production_requires_unique_secret_and_auth():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(APP_MODE="production")
    with pytest.raises(ValueError, match="LOGIN_ENABLED"):
        Settings(APP_MODE="production", LOGIN_ENABLED=False, SECRET_KEY="a" * 32)
    assert Settings(APP_MODE="production", SECRET_KEY="a" * 32).LOGIN_ENABLED


def test_legacy_development_and_local_mode_remain_supported():
    assert Settings().SECRET_KEY == "HIPPOBOX_DEV_SECRET"
    assert not Settings(LOGIN_ENABLED=False, EMAIL_ENABLED=True).EMAIL_ENABLED
