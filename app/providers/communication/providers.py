import logging
from typing import Any, Dict, Optional
from app.providers.communication.base import (
    EmailProvider,
    PushNotificationProvider,
    SMSProvider,
    WhatsAppProvider,
)

logger = logging.getLogger(__name__)


class SmtpEmailProvider(EmailProvider):
    """
    SMTP Email Provider implementation.
    """
    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 1025, sender: str = "noreply@apnaerp.io"):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender

    async def send_email(self, to_email: str, subject: str, body_html: str, from_email: Optional[str] = None) -> bool:
        logger.info(f"[SMTP] Sending email to {to_email} | Subject: {subject}")
        return True


class TwilioSmsProvider(SMSProvider):
    """
    Twilio / AWS SNS SMS Provider implementation.
    """
    def __init__(self, account_sid: str = "AC_mock", auth_token: str = "auth_mock", from_number: str = "+18005550199"):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send_sms(self, phone_number: str, message: str) -> bool:
        logger.info(f"[Twilio SMS] Sending SMS to {phone_number}: {message}")
        return True


class MetaCloudWhatsAppProvider(WhatsAppProvider):
    """
    Meta Cloud API WhatsApp Provider implementation.
    """
    def __init__(self, phone_number_id: str = "10001", access_token: str = "EAAG_mock"):
        self.phone_number_id = phone_number_id
        self.access_token = access_token

    async def send_whatsapp(self, phone_number: str, template_name: str, parameters: Dict[str, Any]) -> bool:
        logger.info(f"[WhatsApp] Sending template {template_name} to {phone_number}")
        return True


class FirebasePushNotificationProvider(PushNotificationProvider):
    """
    Firebase Cloud Messaging (FCM) Push Notification Provider implementation.
    """
    def __init__(self, fcm_server_key: str = "fcm_key_mock"):
        self.fcm_server_key = fcm_server_key

    async def send_push_notification(self, device_token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        logger.info(f"[FCM Push] Sending push notification to {device_token[:10]}... | Title: {title}")
        return True
