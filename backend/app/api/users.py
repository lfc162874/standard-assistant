"""用户接口：当前用户资料查询与修改。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from app.services.auth_service import change_password, get_current_user, update_profile
from app.services.user_service import UserRecord

router = APIRouter()


class UserProfileResponse(BaseModel):
    id: str
    username: str
    nickname: str | None
    email: str | None
    phone: str | None
    avatar_url: str | None
    role: str
    status: str
    created_at: datetime
    last_login_at: datetime | None


class UserProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = Field(default=None, max_length=500)


class PasswordUpdateRequest(BaseModel):
    old_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class OkResponse(BaseModel):
    ok: bool


def _to_profile(user: UserRecord) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        email=user.email,
        phone=user.phone,
        avatar_url=user.avatar_url,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/users/me", response_model=UserProfileResponse)
def me(current_user: Annotated[UserRecord, Depends(get_current_user)]) -> UserProfileResponse:
    return _to_profile(current_user)


@router.patch("/users/me", response_model=UserProfileResponse)
def patch_me(
    payload: UserProfileUpdateRequest,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
) -> UserProfileResponse:
    updates = payload.model_dump(exclude_unset=True)
    raw_email = updates.get("email", current_user.email)
    normalized_email = str(raw_email) if raw_email is not None else None

    next_user = update_profile(
        user=current_user,
        nickname=updates.get("nickname", current_user.nickname),
        email=normalized_email,
        phone=updates.get("phone", current_user.phone),
        avatar_url=updates.get("avatar_url", current_user.avatar_url),
    )
    return _to_profile(next_user)


@router.post("/users/me/password", response_model=OkResponse)
def patch_password(
    payload: PasswordUpdateRequest,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
) -> OkResponse:
    change_password(
        user=current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return OkResponse(ok=True)
