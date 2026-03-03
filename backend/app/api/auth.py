"""认证接口：注册、登录、刷新、退出。"""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from app.services import auth_service
from app.services.token_service import TokenValidationError, decode_token
from app.services.user_service import UserRecord, get_user_by_id

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    nickname: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class UserProfile(BaseModel):
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


class AuthTokenResponse(BaseModel):
    access_token: str
    access_expires_in: int
    refresh_token: str
    refresh_expires_in: int
    user: UserProfile


class OkResponse(BaseModel):
    ok: bool


def _to_profile(user: UserRecord) -> UserProfile:
    return UserProfile(
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


def _client_meta(request: Request) -> tuple[str, str]:
    ip = (request.client.host if request.client else "unknown").strip() or "unknown"
    user_agent = request.headers.get("user-agent", "").strip()
    return ip, user_agent


@router.post("/auth/register", response_model=UserProfile)
def register(payload: RegisterRequest) -> UserProfile:
    user = auth_service.register(
        username=payload.username,
        password=payload.password,
        nickname=payload.nickname,
        email=str(payload.email) if payload.email is not None else None,
        phone=payload.phone,
    )
    return _to_profile(user)


@router.post("/auth/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, request: Request) -> AuthTokenResponse:
    ip, user_agent = _client_meta(request)
    result = auth_service.login(
        username=payload.username,
        password=payload.password,
        ip=ip,
        user_agent=user_agent,
    )
    return AuthTokenResponse(
        access_token=result.tokens.access_token,
        access_expires_in=result.tokens.access_expires_in,
        refresh_token=result.tokens.refresh_token,
        refresh_expires_in=result.tokens.refresh_expires_in,
        user=_to_profile(result.user),
    )


@router.post("/auth/refresh", response_model=AuthTokenResponse)
def refresh(payload: RefreshRequest, request: Request) -> AuthTokenResponse:
    ip, user_agent = _client_meta(request)
    tokens = auth_service.refresh(
        refresh_token=payload.refresh_token,
        ip=ip,
        user_agent=user_agent,
    )
    try:
        token_payload = decode_token(tokens.access_token, expected_type="access")
    except TokenValidationError as exc:
        raise RuntimeError("刷新后 access token 解析失败") from exc
    current_user = get_user_by_id(str(token_payload["sub"]))
    if current_user is None:
        raise RuntimeError("刷新后用户不存在")

    return AuthTokenResponse(
        access_token=tokens.access_token,
        access_expires_in=tokens.access_expires_in,
        refresh_token=tokens.refresh_token,
        refresh_expires_in=tokens.refresh_expires_in,
        user=_to_profile(current_user),
    )


@router.post("/auth/logout", response_model=OkResponse)
def logout(payload: LogoutRequest) -> OkResponse:
    auth_service.logout(payload.refresh_token)
    return OkResponse(ok=True)
