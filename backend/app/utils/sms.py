"""
短信发送 Provider（可插拔）
dev: 不真实发送，验证码写日志（内测期用，ICP 备案后切腾讯云）
tencent: 腾讯云短信 SDK（TODO，备案通过后实现）
"""
import logging
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class SmsProvider(ABC):
    @abstractmethod
    async def send_code(self, phone: str, code: str) -> bool: ...


class DevSmsProvider(SmsProvider):
    async def send_code(self, phone: str, code: str) -> bool:
        logger.info(f"[DEV SMS] 验证码 {code} → {phone}")
        return True


class TencentSmsProvider(SmsProvider):
    async def send_code(self, phone: str, code: str) -> bool:
        raise NotImplementedError("腾讯云短信待 ICP 备案后接入")


def get_sms_provider() -> SmsProvider:
    if settings.SMS_PROVIDER == "tencent":
        return TencentSmsProvider()
    return DevSmsProvider()
