"""Private profile images; storage failure never replaces the last confirmed photo."""

import hashlib
import json
from collections.abc import AsyncIterable
from io import BytesIO
from uuid import uuid4

from fastapi import Depends
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.error import AuthErrorCode, AuthException
from hippobox.platform.core.object_storage import ObjectStorage, StorageError, StorageErrorCode
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.deps import get_object_storage
from hippobox.platform.models.profile_photo import ProfilePhotos
from hippobox.platform.models.user import UserResponse, Users

logger = get_logger(__name__)
PHOTO_PATH = "/api/v1/auth/me/photo"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def storage_identity() -> str:
    """Nonsecret fingerprint prevents reading/deleting a key in a different location."""
    source = [SETTINGS.OBJECT_STORAGE_PROVIDER]
    if SETTINGS.OBJECT_STORAGE_PROVIDER == "local":
        source.append(str(SETTINGS.OBJECT_STORAGE_LOCAL_ROOT.resolve()))
    else:
        source.extend(
            [
                SETTINGS.OBJECT_STORAGE_S3_ENDPOINT_URL.rstrip("/"),
                SETTINGS.OBJECT_STORAGE_S3_BUCKET,
                SETTINGS.OBJECT_STORAGE_S3_REGION
                if SETTINGS.OBJECT_STORAGE_PROVIDER != "r2"
                else "auto",
            ]
        )
    return hashlib.sha256(json.dumps(source).encode()).hexdigest()


def normalize_image(data: bytes) -> bytes:
    try:
        with Image.open(BytesIO(data), formats=["PNG", "JPEG", "WEBP", "GIF"]) as source:
            if source.width * source.height > 16_000_000:
                raise ValueError("pixel bound")
            source.load()
            image = ImageOps.exif_transpose(source)
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            image = image.convert("RGBA")
            image.info.clear()
            output = BytesIO()
            image.save(output, "WEBP", quality=82, exif=b"", xmp=b"", icc_profile=b"")
            return output.getvalue()
    except (ValueError, OSError, SyntaxError, UnidentifiedImageError, Image.DecompressionBombError):
        raise AuthException(code=AuthErrorCode.PROFILE_PHOTO_INVALID) from None


class ProfilePhotoService:
    def __init__(self, storage: ObjectStorage = Depends(get_object_storage)):
        self.storage = storage

    async def cleanup(self, reference: dict | None) -> None:
        if not reference:
            return
        if reference.get("storage") != storage_identity():
            logger.warning(
                "Profile photo cleanup requires original storage (key=%s).", reference.get("key")
            )
            return
        try:
            await self.storage.delete(reference["key"])
        except StorageError as exc:
            logger.warning(
                "Profile photo cleanup deferred (key=%s, code=%s).",
                reference["key"],
                exc.code.value,
            )

    async def _compensate(self, user_id: int, reference: dict) -> None:
        # Commit errors can be ambiguous: never delete a key without checking DB truth.
        try:
            current = await ProfilePhotos.get(user_id)
        except AuthException as exc:
            if exc.code != AuthErrorCode.USER_NOT_FOUND.code:
                raise
        except SQLAlchemyError:
            logger.warning(
                "Profile photo compensation requires DB review (key=%s).", reference["key"]
            )
            return
        else:
            if current.reference == reference:
                return
        await self.cleanup(reference)

    async def upload(self, user_id: int, chunks: AsyncIterable[bytes]) -> UserResponse:
        previous = await ProfilePhotos.get(user_id)
        data = bytearray()
        async for chunk in chunks:
            if len(data) + len(chunk) > MAX_UPLOAD_BYTES:
                raise AuthException(code=AuthErrorCode.PROFILE_PHOTO_TOO_LARGE)
            data.extend(chunk)
        encoded = await run_in_threadpool(normalize_image, bytes(data))
        version = uuid4().hex
        reference = {
            "key": f"profile-photos/{user_id}/{version}.webp",
            "storage": storage_identity(),
        }
        try:
            await self.storage.put(reference["key"], encoded, "image/webp")
        except StorageError:
            # A failed remote response may still have written the immutable key.
            await self.cleanup(reference)
            raise AuthException(code=AuthErrorCode.PROFILE_PHOTO_UNAVAILABLE) from None
        try:
            changed = await ProfilePhotos.replace(
                user_id, previous.url, f"{PHOTO_PATH}?version={version}", reference
            )
        except SQLAlchemyError:
            await self._compensate(user_id, reference)
            raise AuthException(code=AuthErrorCode.PROFILE_UPDATE_FAILED) from None
        if not changed:
            await self.cleanup(reference)
            raise AuthException(code=AuthErrorCode.PROFILE_PHOTO_CONFLICT)
        await self.cleanup(previous.reference)
        user = await Users.get_user_response_by_id(user_id)
        if user is None:
            raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)
        return user

    async def delete(self, user_id: int) -> UserResponse:
        previous = await ProfilePhotos.get(user_id)
        try:
            changed = await ProfilePhotos.replace(user_id, previous.url, None, None)
        except SQLAlchemyError:
            raise AuthException(code=AuthErrorCode.PROFILE_UPDATE_FAILED) from None
        if not changed:
            raise AuthException(code=AuthErrorCode.PROFILE_PHOTO_CONFLICT)
        await self.cleanup(previous.reference)
        user = await Users.get_user_response_by_id(user_id)
        if user is None:
            raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)
        return user

    async def read(self, user_id: int, version: str | None) -> bytes:
        current = await ProfilePhotos.get(user_id)
        if not current.reference or (version and current.url != f"{PHOTO_PATH}?version={version}"):
            raise AuthException(code=AuthErrorCode.PROFILE_PHOTO_NOT_FOUND)
        if current.reference.get("storage") != storage_identity():
            raise AuthException(code=AuthErrorCode.PROFILE_PHOTO_UNAVAILABLE)
        try:
            return (await self.storage.get(current.reference["key"])).data
        except StorageError as exc:
            code = (
                AuthErrorCode.PROFILE_PHOTO_NOT_FOUND
                if exc.code == StorageErrorCode.NOT_FOUND
                else AuthErrorCode.PROFILE_PHOTO_UNAVAILABLE
            )
            raise AuthException(code=code) from None
