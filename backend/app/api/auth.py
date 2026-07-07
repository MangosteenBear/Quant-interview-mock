"""
账号认证接口：验证码发送、登录/注册、token 刷新
"""
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.config import settings
from app.models import User, VerificationCode
from app.schemas.auth import (
    RefreshRequest,
    RefreshResponse,
    SendCodeRequest,
    SendCodeResponse,
    TokenResponse,
    VerifyRequest,
)
from app.utils.security import create_token, decode_token
from app.utils.sms import get_sms_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["认证"])

CODE_TTL_MINUTES = 5
RESEND_INTERVAL_SECONDS = 60


@router.post("/send-code", response_model=SendCodeResponse, summary="发送验证码")
async def send_code(body: SendCodeRequest, db: AsyncSession = Depends(get_session)):
    now = datetime.now()

    # 60 秒内不允许重发
    recent = (await db.execute(
        select(VerificationCode)
        .where(VerificationCode.phone == body.phone)
        .order_by(VerificationCode.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if recent and (now - recent.created_at).total_seconds() < RESEND_INTERVAL_SECONDS:
        raise HTTPException(status_code=429, detail="发送过于频繁，请稍后再试")

    code = f"{secrets.randbelow(1000000):06d}"
    db.add(VerificationCode(
        phone=body.phone,
        code=code,
        expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
        created_at=now,  # 显式本地时间，避免 func.now() 的 DB 时区与应用比较不一致
    ))
    await db.commit()

    await get_sms_provider().send_code(body.phone, code)
    return SendCodeResponse(
        sent=True,
        dev_code=code if settings.SMS_PROVIDER == "dev" else None,
    )


@router.post("/verify", response_model=TokenResponse, summary="验证码登录/注册")
async def verify(body: VerifyRequest, db: AsyncSession = Depends(get_session)):
    vc = (await db.execute(
        select(VerificationCode)
        .where(
            VerificationCode.phone == body.phone,
            VerificationCode.code == body.code,
            VerificationCode.used == False,  # noqa: E712
            VerificationCode.expires_at > datetime.now(),
        )
        .order_by(VerificationCode.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not vc:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    vc.used = True

    user = (await db.execute(
        select(User).where(User.phone == body.phone)
    )).scalar_one_or_none()
    is_new = user is None
    if is_new:
        user = User(phone=body.phone, nickname=f"用户{body.phone[-4:]}")
        db.add(user)
        await db.flush()

    user.last_active_at = datetime.now()
    await db.commit()

    return TokenResponse(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
        is_new_user=is_new,
    )


@router.post("/refresh", response_model=RefreshResponse, summary="刷新 access token")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_session)):
    user_id = decode_token(body.refresh_token, expect_type="refresh")
    if user_id is None:
        raise HTTPException(status_code=401, detail="refresh token 无效或已过期")
    exists = (await db.execute(
        select(User.id).where(User.id == user_id)
    )).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=401, detail="用户不存在")
    return RefreshResponse(access_token=create_token(user_id, "access"))
