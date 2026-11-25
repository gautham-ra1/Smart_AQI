"""Authentication endpoints: register, login, refresh, current user."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, success_response
from app.core.permissions import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth_schema import LoginRequest, RefreshRequest, RegisterRequest

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _user_dict(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "health_profile": u.health_profile,
        "created_at": u.created_at.isoformat(),
    }


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise AppError(409, "EMAIL_EXISTS", "An account with this email already exists.")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="citizen",
        health_profile=payload.health_profile,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id), user.email, user.role)
    refresh_token = create_refresh_token(str(user.id), user.email, user.role)
    return success_response(
        {
            "user": _user_dict(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
        status_code=201,
    )


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = res.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "This account has been deactivated.")

    access_token = create_access_token(str(user.id), user.email, user.role)
    refresh_token = create_refresh_token(str(user.id), user.email, user.role)
    return success_response(
        {
            "user": _user_dict(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    )


@router.post("/refresh")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise AppError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired.")

    res = await db.execute(select(User).where(User.id == uuid.UUID(str(decoded["sub"]))))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise AppError(401, "USER_INACTIVE", "Account not found or inactive.")

    return success_response(
        {
            "access_token": create_access_token(str(user.id), user.email, user.role),
            "token_type": "bearer",
        }
    )


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return success_response(_user_dict(current_user))
