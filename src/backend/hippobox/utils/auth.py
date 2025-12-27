from typing import Annotated

from fastapi import BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import ValidationError

from hippobox.core.settings import SETTINGS
from hippobox.models.api_key import APIKeys
from hippobox.models.user import UserResponse, UserRole, Users
from hippobox.utils.security import hash_api_key

security = HTTPBearer()


async def get_current_user(
    background_tasks: BackgroundTasks, token_auth: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> UserResponse:
    token = token_auth.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # ---------------------------
    # API Key Authentication
    # ---------------------------
    if token.startswith("sk-"):
        hashed_input = hash_api_key(token)

        api_key_record = await APIKeys.get_by_hash(hashed_input)

        if not api_key_record or not api_key_record.is_active:
            raise credentials_exception

        user = await Users.get(api_key_record.user_id)
        if user is None:
            raise credentials_exception

        background_tasks.add_task(APIKeys.update_usage, api_key_record.id)

        return UserResponse.model_validate(user.model_dump())

    # ---------------------------
    # JWT Authentication
    # ---------------------------
    else:
        try:
            payload = jwt.decode(token, SETTINGS.SECRET_KEY, algorithms=[SETTINGS.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
            user_id_int = int(user_id)
        except (JWTError, ValidationError, ValueError):
            raise credentials_exception

        user = await Users.get(user_id_int)
        if user is None:
            raise credentials_exception

    return UserResponse.model_validate(user.model_dump())


async def require_admin(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
