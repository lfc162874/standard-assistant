"""认证服务：处理注册、登录、刷新、登出与鉴权依赖。"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.core.settings import (
    get_auth_register_enabled,
    get_login_lock_minutes,
    get_login_max_retries,
)
from app.services.token_service import TokenPair, TokenValidationError, create_token_pair, decode_token, hash_refresh_token
from app.services.user_service import (
    SessionOwnershipError,
    UserConflictError,
    UserNotFoundError,
    UserRecord,
    clear_failed_logins,
    count_recent_failed_logins,
    create_user,
    get_user_by_id,
    get_user_by_username,
    get_valid_refresh_token,
    insert_refresh_token,
    record_login_attempt,
    revoke_refresh_token,
    touch_last_login,
    update_password,
    update_user_profile,
)

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
MAX_BCRYPT_PASSWORD_BYTES = 72


@dataclass
class AuthResult:
    tokens: TokenPair
    user: UserRecord


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text if text else None


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)


def _raise_http(status_code: int, detail: str) -> None:
    raise HTTPException(status_code=status_code, detail=detail)


def _assert_password_length(raw_password: str, field_name: str = "密码") -> None:
    """bcrypt 仅支持前 72 字节，超出会造成截断或报错。"""

    if len(raw_password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        _raise_http(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{field_name}长度不能超过 {MAX_BCRYPT_PASSWORD_BYTES} 字节",
        )


def _assert_active_user(user: UserRecord) -> None:
    if user.status != "active":
        _raise_http(status.HTTP_403_FORBIDDEN, "账号已禁用")


def register(
    *,
    username: str,
    password: str,
    nickname: str | None,
    email: str | None,
    phone: str | None,
) -> UserRecord:
    if not get_auth_register_enabled():
        _raise_http(status.HTTP_403_FORBIDDEN, "当前环境已关闭注册")

    cleaned_username = username.strip()
    if not cleaned_username:
        _raise_http(status.HTTP_422_UNPROCESSABLE_ENTITY, "用户名不能为空")

    if len(password) < 8:
        _raise_http(status.HTTP_422_UNPROCESSABLE_ENTITY, "密码长度不能小于 8 位")
    _assert_password_length(password)

    try:
        user = create_user(
            username=cleaned_username,
            password_hash=hash_password(password),
            nickname=_normalize_text(nickname),
            email=_normalize_text(email),
            phone=_normalize_text(phone),
        )
    except UserConflictError as exc:
        _raise_http(status.HTTP_409_CONFLICT, str(exc))

    logger.info("audit.register.success username=%s user_id=%s", user.username, user.id)
    return user


def _is_locked(username: str, ip: str) -> bool:
    failed_count = count_recent_failed_logins(username, ip, get_login_lock_minutes())
    return failed_count >= get_login_max_retries()


def login(*, username: str, password: str, ip: str, user_agent: str) -> AuthResult:
    cleaned_username = username.strip()
    _assert_password_length(password)

    if _is_locked(cleaned_username, ip):
        logger.warning("audit.login.locked username=%s ip=%s", cleaned_username, ip)
        _raise_http(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"登录失败次数过多，请 {get_login_lock_minutes()} 分钟后重试",
        )

    user = get_user_by_username(cleaned_username)
    if user is None or not verify_password(password, user.password_hash):
        record_login_attempt(cleaned_username, ip, success=False)
        logger.warning("audit.login.failed username=%s ip=%s", cleaned_username, ip)
        if _is_locked(cleaned_username, ip):
            _raise_http(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"登录失败次数过多，请 {get_login_lock_minutes()} 分钟后重试",
            )
        _raise_http(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    _assert_active_user(user)
    clear_failed_logins(cleaned_username, ip)
    record_login_attempt(cleaned_username, ip, success=True)

    tokens = create_token_pair(user.id)
    insert_refresh_token(
        user_id=user.id,
        token_hash=hash_refresh_token(tokens.refresh_token),
        expires_at=tokens.refresh_expires_at,
        ip=ip,
        user_agent=user_agent,
    )
    touch_last_login(user.id)

    latest_user = get_user_by_id(user.id)
    if latest_user is None:
        _raise_http(status.HTTP_500_INTERNAL_SERVER_ERROR, "登录状态异常，请重试")

    logger.info("audit.login.success username=%s user_id=%s ip=%s", latest_user.username, latest_user.id, ip)
    return AuthResult(tokens=tokens, user=latest_user)


def refresh(*, refresh_token: str, ip: str, user_agent: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenValidationError:
        _raise_http(status.HTTP_401_UNAUTHORIZED, "refresh_token 无效或已过期")

    user_id = str(payload["sub"])
    stored = get_valid_refresh_token(hash_refresh_token(refresh_token))
    if stored is None:
        _raise_http(status.HTTP_401_UNAUTHORIZED, "refresh_token 无效或已失效")
    if str(stored["user_id"]) != user_id:
        _raise_http(status.HTTP_401_UNAUTHORIZED, "refresh_token 与用户不匹配")

    user = get_user_by_id(user_id)
    if user is None:
        _raise_http(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    _assert_active_user(user)

    next_tokens = create_token_pair(user_id)
    revoke_refresh_token(hash_refresh_token(refresh_token))
    insert_refresh_token(
        user_id=user_id,
        token_hash=hash_refresh_token(next_tokens.refresh_token),
        expires_at=next_tokens.refresh_expires_at,
        ip=ip,
        user_agent=user_agent,
    )

    logger.info("audit.refresh.success user_id=%s ip=%s", user_id, ip)
    return next_tokens


def logout(refresh_token: str) -> None:
    try:
        decode_token(refresh_token, expected_type="refresh")
        token_hash = hash_refresh_token(refresh_token)
    except TokenValidationError:
        logger.info("audit.logout.invalid_token")
        return

    revoke_refresh_token(token_hash)
    logger.info("audit.logout.success")


def change_password(*, user: UserRecord, old_password: str, new_password: str) -> None:
    if len(new_password) < 8:
        _raise_http(status.HTTP_422_UNPROCESSABLE_ENTITY, "新密码长度不能小于 8 位")
    _assert_password_length(new_password, "新密码")

    if not verify_password(old_password, user.password_hash):
        _raise_http(status.HTTP_401_UNAUTHORIZED, "旧密码不正确")

    update_password(user.id, hash_password(new_password))
    logger.info("audit.password.changed user_id=%s", user.id)


def update_profile(
    *,
    user: UserRecord,
    nickname: str | None,
    email: str | None,
    phone: str | None,
    avatar_url: str | None,
) -> UserRecord:
    try:
        return update_user_profile(
            user.id,
            nickname=_normalize_text(nickname),
            email=_normalize_text(email),
            phone=_normalize_text(phone),
            avatar_url=_normalize_text(avatar_url),
        )
    except UserConflictError as exc:
        _raise_http(status.HTTP_409_CONFLICT, str(exc))
    except UserNotFoundError as exc:
        _raise_http(status.HTTP_404_NOT_FOUND, str(exc))


def _resolve_access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        _raise_http(status.HTTP_401_UNAUTHORIZED, "未认证，请先登录")
    return credentials.credentials


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserRecord:
    access_token = _resolve_access_token(credentials)

    try:
        payload = decode_token(access_token, expected_type="access")
    except TokenValidationError:
        _raise_http(status.HTTP_401_UNAUTHORIZED, "访问令牌无效或已过期")

    user_id = str(payload["sub"])
    user = get_user_by_id(user_id)
    if user is None:
        _raise_http(status.HTTP_401_UNAUTHORIZED, "用户不存在")

    _assert_active_user(user)
    return user


__all__ = [
    "AuthResult",
    "SessionOwnershipError",
    "change_password",
    "get_current_user",
    "login",
    "logout",
    "refresh",
    "register",
    "update_profile",
]
