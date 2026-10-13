"""Photo reference persistence with compare-and-swap against the visible revision."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update

from hippobox.platform.core.db.session import get_db
from hippobox.platform.core.error import AuthErrorCode, AuthException
from hippobox.platform.models.user import User


@dataclass(frozen=True)
class PhotoSnapshot:
    url: str | None
    reference: dict | None


class ProfilePhotos:
    @staticmethod
    async def get(user_id: int) -> PhotoSnapshot:
        async with get_db() as db:
            row = (
                await db.execute(
                    select(User.profile_image_url, User.profile_photo).where(
                        User.id == user_id, User.is_active.is_(True)
                    )
                )
            ).first()
            if row is None:
                raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)
            return PhotoSnapshot(row.profile_image_url, row.profile_photo)

    @staticmethod
    async def replace(
        user_id: int, expected_url: str | None, url: str | None, reference: dict | None
    ) -> bool:
        async with get_db() as db:
            result = await db.execute(
                update(User)
                .where(
                    User.id == user_id,
                    User.is_active.is_(True),
                    User.profile_image_url == expected_url,
                )
                .values(
                    profile_image_url=url, profile_photo=reference, updated_at=datetime.now(UTC)
                )
            )
            await db.commit()
            return result.rowcount == 1
