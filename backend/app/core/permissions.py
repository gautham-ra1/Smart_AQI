"""RBAC and JWT authentication dependencies."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED", "Missing or invalid Authorization Bearer token.")

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise AppError(401, "INVALID_TOKEN", "Access token is invalid or expired.")

    try:
        user_uuid = uuid.UUID(str(payload["sub"]))
    except ValueError:
        raise AppError(401, "INVALID_TOKEN", "Malformed token subject.")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AppError(401, "USER_INACTIVE", "Account not found or inactive.")
    return user


def require_roles(*allowed_roles: str) -> Callable:
    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AppError(
                403,
                "FORBIDDEN",
                f"Role '{current_user.role}' is not authorized. Required: {', '.join(allowed_roles)}.",
            )
        return current_user

    return _guard
