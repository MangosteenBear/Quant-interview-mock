"""
用户接口：当前用户信息、历史数据绑定
"""
from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import AttemptLog, Favorite, User
from app.schemas.auth import BindDeviceRequest, BindDeviceResponse, UserOut

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", response_model=UserOut, summary="当前用户信息")
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/me/bind-device", response_model=BindDeviceResponse, summary="绑定设备历史记录到账号")
async def bind_device(
    body: BindDeviceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    r1 = await db.execute(
        update(AttemptLog)
        .where(AttemptLog.device_id == body.device_id, AttemptLog.user_id.is_(None))
        .values(user_id=user.id)
    )
    r2 = await db.execute(
        update(Favorite)
        .where(Favorite.device_id == body.device_id, Favorite.user_id.is_(None))
        .values(user_id=user.id)
    )
    await db.commit()
    return BindDeviceResponse(
        migrated_attempts=r1.rowcount or 0,
        migrated_favorites=r2.rowcount or 0,
    )
