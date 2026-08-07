from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class EmailProvider(ABC):
    @abstractmethod
    async def send_email(self, to_email: str, subject: str, body_html: str, from_email: Optional[str] = None) -> bool:
        pass


class SMSProvider(ABC):
    @abstractmethod
    async def send_sms(self, phone_number: str, message: str) -> bool:
        pass


class WhatsAppProvider(ABC):
    @abstractmethod
    async def send_whatsapp(self, phone_number: str, template_name: str, parameters: Dict[str, Any]) -> bool:
        pass


class PushNotificationProvider(ABC):
    @abstractmethod
    async def send_push_notification(self, device_token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        pass
