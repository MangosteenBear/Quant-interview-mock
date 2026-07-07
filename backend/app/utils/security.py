"""
JWT 签发与校验
access token 7 天，refresh token 30 天
"""
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

ALGORITHM = "HS256"


def create_token(user_id: int, token_type: str = "access") -> str:
    days = settings.ACCESS_TOKEN_DAYS if token_type == "access" else settings.REFRESH_TOKEN_DAYS
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "exp": datetime.now(timezone.utc) + timedelta(days=days),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str, expect_type: str = "access") -> int | None:
    """返回 user_id，无效/过期/类型不符返回 None"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expect_type:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None
