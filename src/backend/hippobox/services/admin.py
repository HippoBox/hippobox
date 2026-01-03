import logging

from fastapi import Request

from hippobox.errors.admin import AdminErrorCode, AdminException
from hippobox.errors.service import raise_exception_with_log
from hippobox.models.user import UserModel, Users
from hippobox.core.redis import RedisManager

log = logging.getLogger("admin")


class AdminService:
    @staticmethod
    async def _clear_token_set(redis, set_key: str, token_prefix: str):
        tokens = await redis.smembers(set_key)
        if tokens:
            for raw in tokens:
                token = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                await redis.delete(f"{token_prefix}:{token}")
        await redis.delete(set_key)

    async def list_users(self) -> list[UserModel]:
        try:
            return await Users.get_list()
        except Exception as e:
            raise_exception_with_log(AdminErrorCode.LIST_USERS_FAILED, e)

    async def delete_user(self, user_id: int) -> bool:
        try:
            deleted = await Users.delete(user_id)
        except Exception as e:
            raise_exception_with_log(AdminErrorCode.DELETE_USER_FAILED, e)

        if not deleted:
            raise AdminException(AdminErrorCode.USER_NOT_FOUND)

        try:
            redis = await RedisManager.get_client()
            await redis.delete(f"refresh_token:{user_id}")
            await redis.delete(f"login_fail:{user_id}")
            await self._clear_token_set(redis, f"email_verify_user:{user_id}", "email_verify")
            await self._clear_token_set(redis, f"reset_pw_user:{user_id}", "reset_pw")
        except Exception as e:
            log.warning("Failed to clear login_fail for %s: %s", user_id, e)

        return True


def get_admin_service(request: Request) -> AdminService:
    return AdminService()
