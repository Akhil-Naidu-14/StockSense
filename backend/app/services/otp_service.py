from typing import Dict, Optional
import logging
from app.config import settings

logger = logging.getLogger("stocksense.otp")


class OTPService:
    """Service abstraction for generating, delivering, and storing test OTPs."""

    _dev_otp_store: Dict[str, str] = {}

    @classmethod
    def send_otp(cls, email: str, otp_code: str) -> None:
        """
        Deliver OTP code to the given user's email.
        In non-production environments, the OTP is stored in memory for testing/dev access.
        """
        email_key = email.strip().lower()
        if settings.APP_ENV != "production":
            cls._dev_otp_store[email_key] = otp_code
            logger.info(f"[DEV ONLY] OTP for {email_key}: {otp_code}")
        else:
            # Production delivery logic (e.g. SMTP / SMS provider integration)
            logger.info(f"OTP dispatch initiated for user {email_key}")

    @classmethod
    def get_dev_otp(cls, email: str) -> Optional[str]:
        """
        Retrieve captured OTP for an email in non-production environments.
        Returns None in production to maintain strict security boundaries.
        """
        if settings.APP_ENV == "production":
            return None
        return cls._dev_otp_store.get(email.strip().lower())

    @classmethod
    def clear_dev_otps(cls) -> None:
        """Clear test OTP store."""
        cls._dev_otp_store.clear()
