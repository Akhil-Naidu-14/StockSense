from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user
from app.models import PasswordResetOTP, User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginResponse,
    MessageResponse,
    ResetPasswordRequest,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.services.otp_service import OTPService
from app.utils.security import (
    create_access_token,
    create_password_reset_token,
    decode_jwt_token,
    hash_otp,
    hash_password,
    verify_otp_hash,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def signup(payload: UserSignupRequest, db: Session = Depends(get_db)):
    """Register a new user with INVENTORY_MANAGER or WAREHOUSE_STAFF role."""
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    return user


@router.post("/login", response_model=LoginResponse, summary="User authentication")
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email and password, returning a JWT access token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    access_token = create_access_token(user_id=user.id, role=user.role.value)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user")
def get_me(current_user: User = Depends(get_current_active_user)):
    """Return profile details for the currently authenticated active user."""
    return current_user


@router.post("/logout", response_model=MessageResponse, summary="User logout")
def logout(current_user: User = Depends(get_current_active_user)):
    """
    Stateless logout endpoint.

    Because JWT access tokens are stateless, clients must discard the stored token upon
    receiving this response.
    """
    return MessageResponse(
        message="Logged out successfully. Please discard the access token on the client side."
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Initiate password reset OTP flow",
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request a 6-digit numeric password reset OTP.
    Returns a uniform generic response regardless of user existence to prevent account enumeration.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if user and user.is_active:
        # Generate 6-digit numeric OTP using Python `secrets` module
        otp_code = "".join(secrets.choice("0123456789") for _ in range(6))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Store hashed OTP for security
        otp_record = PasswordResetOTP(
            user_id=user.id,
            otp=hash_otp(otp_code),
            expires_at=expires_at,
            verified=False,
            used=False,
        )
        db.add(otp_record)
        db.commit()

        # Send OTP via abstract service
        OTPService.send_otp(user.email, otp_code)

    return MessageResponse(
        message="If the email is registered, a password reset OTP has been generated."
    )


@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
    summary="Verify password reset OTP",
)
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify submitted OTP code and return a short-lived password reset token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP",
        )

    now = datetime.now(timezone.utc)
    # Fetch recent unverified and unused OTP records for user
    otp_records = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.verified.is_(False),
            PasswordResetOTP.used.is_(False),
            PasswordResetOTP.expires_at > now,
        )
        .order_by(PasswordResetOTP.id.desc())
        .all()
    )

    matching_otp = None
    for record in otp_records:
        if verify_otp_hash(payload.otp, record.otp):
            matching_otp = record
            break

    if not matching_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP",
        )

    matching_otp.verified = True
    db.commit()

    reset_token = create_password_reset_token(
        user_id=user.id, otp_id=matching_otp.id
    )

    return VerifyOTPResponse(
        reset_token=reset_token,
        token_type="bearer",
        message="OTP verified successfully.",
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset user password using reset token",
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset user password using the short-lived password reset token received after OTP verification."""
    try:
        jwt_payload = decode_jwt_token(payload.reset_token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    if jwt_payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token purpose: password reset token required",
        )

    sub = jwt_payload.get("sub")
    otp_id = jwt_payload.get("otp_id")

    if not sub or not otp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token structure",
        )

    try:
        user_id = int(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token subject",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    otp_record = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.id == otp_id,
            PasswordResetOTP.user_id == user.id,
        )
        .first()
    )

    if not otp_record or not otp_record.verified or otp_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset authorization has expired or already been used",
        )

    user.password_hash = hash_password(payload.new_password)
    otp_record.used = True
    db.commit()

    return MessageResponse(message="Password has been reset successfully.")
