"""Token 服务：负责 JWT 签发、校验与 refresh token 哈希。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from typing import Any

import jwt

from app.core.settings import (
    get_access_token_expire_minutes,
    get_jwt_secret_key,
    get_refresh_token_expire_days,
)

ALGORITHM = "HS256"


class TokenValidationError(ValueError):
    """Token 无效或过期。"""


@dataclass
class TokenPair:
    access_token: str
    access_expires_in: int
    refresh_token: str
    refresh_expires_in: int
    refresh_expires_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, get_jwt_secret_key(), algorithm=ALGORITHM)


def create_access_token(user_id: str) -> tuple[str, int]:
    """为用户签发 access token。"""

    expire_seconds = max(get_access_token_expire_minutes(), 1) * 60
    issued_at = _now()
    expires_at = issued_at + timedelta(seconds=expire_seconds)

    token = _encode(
        {
            "sub": user_id,
            "type": "access",
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
    )
    return token, expire_seconds


def create_refresh_token(user_id: str) -> tuple[str, int, datetime]:
    """为用户签发 refresh token。"""

    expire_seconds = max(get_refresh_token_expire_days(), 1) * 24 * 60 * 60
    issued_at = _now()
    expires_at = issued_at + timedelta(seconds=expire_seconds)

    token = _encode(
        {
            "sub": user_id,
            "type": "refresh",
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "nonce": secrets.token_hex(8),
        }
    )
    return token, expire_seconds, expires_at


def create_token_pair(user_id: str) -> TokenPair:
    """签发 access + refresh token。"""

    access_token, access_expires_in = create_access_token(user_id)
    refresh_token, refresh_expires_in, refresh_expires_at = create_refresh_token(user_id)
    return TokenPair(
        access_token=access_token,
        access_expires_in=access_expires_in,
        refresh_token=refresh_token,
        refresh_expires_in=refresh_expires_in,
        refresh_expires_at=refresh_expires_at,
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """校验并解码 JWT。"""

    try:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenValidationError("令牌无效或已过期") from exc

    token_type = str(payload.get("type", "")).strip()
    if token_type != expected_type:
        raise TokenValidationError("令牌类型不正确")

    sub = str(payload.get("sub", "")).strip()
    if not sub:
        raise TokenValidationError("令牌缺少主体标识")

    return payload


def hash_refresh_token(token: str) -> str:
    """对 refresh token 做 SHA-256 哈希，避免明文入库。"""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
