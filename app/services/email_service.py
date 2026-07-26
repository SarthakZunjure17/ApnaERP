import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Union

from app.core.config import settings

logger = logging.getLogger("app.services.email")


class EmailService:
    """
    Service layer handling email message generation and SMTP delivery.
    Safely falls back to structured logging when SMTP credentials are unconfigured.
    """
    def send_email(
        self,
        *,
        recipient_email: str,
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
    ) -> bool:
        """
        Sends an email via SMTP. If SMTP host is not configured, logs email cleanly.
        """
        sender = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        logger.info(f"[EMAIL SERVICE] Preparing email to '{recipient_email}' | Subject: '{subject}'")

        if not settings.SMTP_HOST:
            logger.info(
                f"[EMAIL MOCK LOG]\nTo: {recipient_email}\nFrom: {sender}\nSubject: {subject}\nBody: {body_text or body_html}"
            )
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient_email

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            if settings.SMTP_TLS:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.sendmail(settings.EMAILS_FROM_EMAIL, [recipient_email], msg.as_string())
            server.quit()
            logger.info(f"[EMAIL SERVICE] Successfully sent email to '{recipient_email}' via SMTP.")
            return True
        except Exception as e:
            logger.error(f"[EMAIL SERVICE] Failed to send email to '{recipient_email}': {e}")
            return False


email_service = EmailService()
