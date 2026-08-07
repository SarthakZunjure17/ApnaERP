import pyotp
from typing import Dict, Tuple


class MultiFactorAuthService:
    """
    Multi-Factor Authentication (MFA) service using TOTP (Google Authenticator / Authy) and Backup Codes.
    """
    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, email: str, issuer: str = "ApnaERP") -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)

    def verify_code(self, secret: str, code: str) -> bool:
        if not secret or not code:
            return False
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
