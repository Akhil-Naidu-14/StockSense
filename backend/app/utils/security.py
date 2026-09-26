from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext
from app.config import settings

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt after validating length constraints."""
    validate_password_strength(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> None:
    """Validate password strength (minimum 8 chars, non-whitespace, reasonable max length)."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters")
    if not password.strip():
        raise ValueError("Password cannot consist solely of whitespace")


def hash_otp(otp: str) -> str:
    """Hash an OTP code using SHA-256 for secure storage."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def verify_otp_hash(plain_otp: str, hashed_otp: str) -> bool:
    """Verify a plain OTP against its stored hash."""
    return hash_otp(plain_otp) == hashed_otp


def create_access_token(
    user_id: int, role: str, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: Dict[str, Any] = {
        "sub": str(user_id),
        "role": str(role),
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_password_reset_token(
    user_id: int, otp_id: int, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed short-lived JWT specifically for password reset."""
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=15)
    )
    to_encode: Dict[str, Any] = {
        "sub": str(user_id),
        "otp_id": otp_id,
        "type": "password_reset",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token."""
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
