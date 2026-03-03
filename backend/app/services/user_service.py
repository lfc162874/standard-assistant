"""用户与会话数据访问服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg

from app.core.db import get_db_connection


class UserConflictError(ValueError):
    """用户唯一约束冲突。"""


class UserNotFoundError(ValueError):
    """用户不存在。"""


class SessionOwnershipError(PermissionError):
    """会话不属于当前用户。"""


@dataclass
class UserRecord:
    id: str
    username: str
    nickname: str | None
    email: str | None
    phone: str | None
    avatar_url: str | None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
    password_hash: str


def _normalize_user(row: dict[str, Any] | None) -> UserRecord | None:
    if row is None:
        return None

    return UserRecord(
        id=str(row["id"]),
        username=str(row["username"]),
        nickname=row.get("nickname"),
        email=row.get("email"),
        phone=row.get("phone"),
        avatar_url=row.get("avatar_url"),
        role=str(row["role"]),
        status=str(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_login_at=row.get("last_login_at"),
        password_hash=str(row["password_hash"]),
    )


def _parse_uuid(user_id: str) -> UUID:
    try:
        return UUID(user_id)
    except ValueError as exc:
        raise UserNotFoundError("用户不存在") from exc


def _raise_conflict(exc: Exception) -> None:
    constraint_name = ""
    diag = getattr(exc, "diag", None)
    if diag is not None:
        constraint_name = str(getattr(diag, "constraint_name", "") or "")
    detail = f"{constraint_name} {exc}"
    if "users_username_key" in detail:
        raise UserConflictError("用户名已存在") from exc
    if "users_email_key" in detail:
        raise UserConflictError("邮箱已存在") from exc
    if "users_phone_key" in detail:
        raise UserConflictError("手机号已存在") from exc
    raise UserConflictError("用户信息冲突") from exc


def create_user(
    *,
    username: str,
    password_hash: str,
    nickname: str | None,
    email: str | None,
    phone: str | None,
) -> UserRecord:
    """创建用户。"""

    user_id = uuid4()
    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (id, username, password_hash, nickname, email, phone)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING
                        id, username, nickname, email, phone, avatar_url,
                        role, status, created_at, updated_at, last_login_at, password_hash
                    """,
                    (user_id, username, password_hash, nickname, email, phone),
                )
                row = cursor.fetchone()
        except psycopg.errors.UniqueViolation as exc:
            _raise_conflict(exc)

    user = _normalize_user(row)
    if user is None:
        raise RuntimeError("创建用户失败")
    return user


def get_user_by_username(username: str) -> UserRecord | None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, username, nickname, email, phone, avatar_url,
                    role, status, created_at, updated_at, last_login_at, password_hash
                FROM users
                WHERE username = %s
                LIMIT 1
                """,
                (username,),
            )
            return _normalize_user(cursor.fetchone())


def get_user_by_id(user_id: str) -> UserRecord | None:
    parsed = _parse_uuid(user_id)
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, username, nickname, email, phone, avatar_url,
                    role, status, created_at, updated_at, last_login_at, password_hash
                FROM users
                WHERE id = %s
                LIMIT 1
                """,
                (parsed,),
            )
            return _normalize_user(cursor.fetchone())


def touch_last_login(user_id: str) -> None:
    parsed = _parse_uuid(user_id)
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_login_at = NOW(), updated_at = NOW() WHERE id = %s",
                (parsed,),
            )


def update_user_profile(
    user_id: str,
    *,
    nickname: str | None,
    email: str | None,
    phone: str | None,
    avatar_url: str | None,
) -> UserRecord:
    parsed = _parse_uuid(user_id)
    with get_db_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET nickname = %s,
                        email = %s,
                        phone = %s,
                        avatar_url = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING
                        id, username, nickname, email, phone, avatar_url,
                        role, status, created_at, updated_at, last_login_at, password_hash
                    """,
                    (nickname, email, phone, avatar_url, parsed),
                )
                row = cursor.fetchone()
        except psycopg.errors.UniqueViolation as exc:
            _raise_conflict(exc)

    user = _normalize_user(row)
    if user is None:
        raise UserNotFoundError("用户不存在")
    return user


def update_password(user_id: str, password_hash: str) -> None:
    parsed = _parse_uuid(user_id)
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                (password_hash, parsed),
            )
            if cursor.rowcount <= 0:
                raise UserNotFoundError("用户不存在")


def insert_refresh_token(
    *,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
    ip: str,
    user_agent: str,
) -> None:
    parsed = _parse_uuid(user_id)
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO auth_refresh_tokens (id, user_id, token_hash, expires_at, ip, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (uuid4(), parsed, token_hash, expires_at, ip, user_agent),
            )


def get_valid_refresh_token(token_hash: str) -> dict[str, Any] | None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, token_hash, expires_at, revoked_at
                FROM auth_refresh_tokens
                WHERE token_hash = %s
                  AND revoked_at IS NULL
                  AND expires_at > NOW()
                LIMIT 1
                """,
                (token_hash,),
            )
            return cursor.fetchone()


def revoke_refresh_token(token_hash: str) -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth_refresh_tokens
                SET revoked_at = NOW()
                WHERE token_hash = %s
                  AND revoked_at IS NULL
                """,
                (token_hash,),
            )


def count_recent_failed_logins(username: str, ip: str, window_minutes: int) -> int:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM login_attempts
                WHERE username = %s
                  AND ip = %s
                  AND success = FALSE
                  AND created_at >= NOW() - make_interval(mins => %s)
                """,
                (username, ip, window_minutes),
            )
            row = cursor.fetchone()
            return int(row["count"] if row else 0)


def record_login_attempt(username: str, ip: str, success: bool) -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO login_attempts (id, username, ip, success)
                VALUES (%s, %s, %s, %s)
                """,
                (uuid4(), username, ip, success),
            )


def clear_failed_logins(username: str, ip: str) -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM login_attempts WHERE username = %s AND ip = %s AND success = FALSE",
                (username, ip),
            )


def ensure_session_owner(user_id: str, session_id: str) -> None:
    """保证会话归属当前用户。首次访问自动登记。"""

    parsed = _parse_uuid(user_id)
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM chat_sessions WHERE session_id = %s LIMIT 1",
                (session_id,),
            )
            row = cursor.fetchone()

            if row is None:
                cursor.execute(
                    """
                    INSERT INTO chat_sessions (id, user_id, session_id)
                    VALUES (%s, %s, %s)
                    """,
                    (uuid4(), parsed, session_id),
                )
                return

            owner_id = str(row["user_id"])
            if owner_id != str(parsed):
                raise SessionOwnershipError("会话不属于当前用户")

            cursor.execute(
                "UPDATE chat_sessions SET updated_at = NOW() WHERE session_id = %s",
                (session_id,),
            )
