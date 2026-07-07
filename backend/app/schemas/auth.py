"""
账号体系 Schema
"""
import re
from datetime import datetime

from pydantic import BaseModel, field_validator

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


class SendCodeRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        if not PHONE_RE.match(v):
            raise ValueError("手机号格式不正确")
        return v


class SendCodeResponse(BaseModel):
    sent: bool
    dev_code: str | None = None  # 仅 dev provider 返回，生产为 null


class VerifyRequest(SendCodeRequest):
    code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    is_new_user: bool


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str


class UserOut(BaseModel):
    id: int
    phone: str
    nickname: str | None
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BindDeviceRequest(BaseModel):
    device_id: str


class BindDeviceResponse(BaseModel):
    migrated_attempts: int
    migrated_favorites: int
