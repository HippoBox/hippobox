import hashlib
import hmac
import secrets

from sqlalchemy.exc import IntegrityError

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.error import APIKeyErrorCode, APIKeyException
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.core.observability.service import observe_service
from hippobox.platform.core.realtime import APIKeyRealtimeEventType
from hippobox.platform.models.api_key import (
    APIKeyCreateForm,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeys,
    APIKeysResponse,
    APIKeyStatusUpdateForm,
)
from hippobox.platform.services.realtime import RealtimeService

API_KEY_PREFIX = "sk_live_"
API_KEY_SECRET_BYTES = 32
API_KEY_VISIBLE_PREFIX_LENGTH = 12
logger = get_logger("hippobox.platform.service.api_key")


class APIKeyService:
    def __init__(self):
        self._realtime = RealtimeService()

    @observe_service("api_key.create")
    async def create_api_key(self, *, user_id: int, form: APIKeyCreateForm) -> APIKeyCreateResponse:
        raw_api_key = self._generate_api_key()
        key_hash = self._hash_api_key(raw_api_key)
        key_prefix = raw_api_key[:API_KEY_VISIBLE_PREFIX_LENGTH]
        try:
            created = await APIKeys.create_api_key(
                user_id=user_id,
                name=form.name.strip(),
                key_prefix=key_prefix,
                key_hash=key_hash,
                expires_at=form.expires_at,
            )
        except IntegrityError as error:
            message = str(error.orig).lower() if getattr(error, "orig", None) else ""
            if "uq_api_keys_user_name" in message or "api_keys.user_id, api_keys.name" in message:
                logger.debug("API key create rejected: duplicate name (user_id=%s).", user_id)
                raise APIKeyException(code=APIKeyErrorCode.API_KEY_NAME_ALREADY_EXISTS) from error
            logger.debug("API key create failed (user_id=%s).", user_id)
            raise APIKeyException(code=APIKeyErrorCode.API_KEY_CREATE_FAILED) from error

        await self._realtime.publish_user_notification(
            user_id=user_id,
            event_type=APIKeyRealtimeEventType.CREATED,
            payload={"api_key": created.model_dump(mode="json")},
        )
        return APIKeyCreateResponse(api_key=raw_api_key, key=created)

    @observe_service("api_key.list")
    async def list_api_keys(self, *, user_id: int) -> APIKeysResponse:
        keys = await APIKeys.list_api_keys(user_id=user_id)
        return APIKeysResponse(items=keys)

    @observe_service("api_key.delete")
    async def delete_api_key(self, *, user_id: int, api_key_id: int) -> APIKeyResponse:
        deleted = await APIKeys.delete_api_key(user_id=user_id, api_key_id=api_key_id)
        if deleted is None:
            logger.debug(
                "API key delete failed: not found (user_id=%s, api_key_id=%s).", user_id, api_key_id
            )
            raise APIKeyException(code=APIKeyErrorCode.API_KEY_NOT_FOUND)
        await self._realtime.publish_user_notification(
            user_id=user_id,
            event_type=APIKeyRealtimeEventType.DELETED,
            payload={"api_key": deleted.model_dump(mode="json")},
        )
        return deleted

    @observe_service("api_key.update_status")
    async def update_api_key_status(
        self,
        *,
        user_id: int,
        api_key_id: int,
        form: APIKeyStatusUpdateForm,
    ) -> APIKeyResponse:
        updated = await APIKeys.set_api_key_enabled(
            user_id=user_id,
            api_key_id=api_key_id,
            enabled=form.enabled,
        )
        if updated is None:
            logger.debug(
                "API key status update failed: not found (user_id=%s, api_key_id=%s).",
                user_id,
                api_key_id,
            )
            raise APIKeyException(code=APIKeyErrorCode.API_KEY_NOT_FOUND)
        await self._realtime.publish_user_notification(
            user_id=user_id,
            event_type=APIKeyRealtimeEventType.STATUS_UPDATED,
            payload={"api_key": updated.model_dump(mode="json")},
        )
        return updated

    def _generate_api_key(self) -> str:
        secret = secrets.token_urlsafe(API_KEY_SECRET_BYTES)
        return f"{API_KEY_PREFIX}{secret}"

    def _hash_api_key(self, api_key: str) -> str:
        # Persist only a keyed digest so raw API keys cannot be recovered from DB.
        return hmac.new(
            SETTINGS.SECRET_KEY.encode("utf-8"),
            api_key.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
