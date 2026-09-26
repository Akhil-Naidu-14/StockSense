from datetime import datetime, timedelta, timezone
from fastapi import Depends
import pytest

from app.main import app
from app.middleware import require_roles
from app.models import PasswordResetOTP, User, UserRole
from app.services.otp_service import OTPService
from app.utils.security import (
    create_access_token,
    hash_otp,
    verify_password,
)


# Route registered on FastAPI app specifically for testing RBAC dependency
@app.get("/test-rbac-manager-only")
def manager_only_route_handler(
    user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    return {"message": "Manager access granted"}


# 1. Signup succeeds
def test_01_signup_succeeds(client):
    response = client.post(
        "/api/auth/signup",
        json={
            "name": "Alice Manager",
            "email": "alice@example.com",
            "phone": "+1234567890",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice Manager"
    assert data["email"] == "alice@example.com"
    assert data["role"] == "INVENTORY_MANAGER"
    assert "password" not in data
    assert "password_hash" not in data


# 2. Stored password is hashed and differs from plaintext
def test_02_stored_password_is_hashed(client, db_session):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Bob Staff",
            "email": "bob@example.com",
            "password": "SecretPassword123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    user = db_session.query(User).filter(User.email == "bob@example.com").first()
    assert user is not None
    assert user.password_hash != "SecretPassword123!"
    assert user.password_hash.startswith("$2")


# 3. Password hash verifies correctly
def test_03_password_hash_verifies_correctly(client, db_session):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Charlie",
            "email": "charlie@example.com",
            "password": "VerifyPassword123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    user = db_session.query(User).filter(User.email == "charlie@example.com").first()
    assert verify_password("VerifyPassword123!", user.password_hash) is True
    assert verify_password("WrongPassword!", user.password_hash) is False


# 4. Duplicate email returns 409
def test_04_duplicate_email_returns_409(client):
    payload = {
        "name": "Dup User",
        "email": "duplicate@example.com",
        "password": "Password123!",
        "role": "WAREHOUSE_STAFF",
    }
    resp1 = client.post("/api/auth/signup", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/auth/signup", json=payload)
    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "Email is already registered"


# 5. Email normalization works correctly
def test_05_email_normalization_works(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Mixed Case User",
            "email": " mixedCase.User@Example.COM ",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "mixedcase.user@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["email"] == "mixedcase.user@example.com"


# 6. Invalid email is rejected
def test_06_invalid_email_rejected(client):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Bad Email",
            "email": "not-a-valid-email",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    assert resp.status_code == 422


# 7. Invalid role is rejected
def test_07_invalid_role_rejected(client):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Bad Role",
            "email": "badrole@example.com",
            "password": "Password123!",
            "role": "SUPER_ADMIN",
        },
    )
    assert resp.status_code == 422


# 8. Weak/too-short password is rejected
def test_08_weak_password_rejected(client):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Weak Pass",
            "email": "weak@example.com",
            "password": "short",
            "role": "WAREHOUSE_STAFF",
        },
    )
    assert resp.status_code == 422


# 9. Login succeeds with correct credentials
def test_09_login_succeeds(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Login User",
            "email": "login@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"


# 10. Login fails with wrong password
def test_10_login_fails_wrong_password(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "User 10",
            "email": "user10@example.com",
            "password": "CorrectPassword123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "user10@example.com", "password": "WrongPassword123!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


# 11. Login fails with HTTP 403 for inactive user
def test_11_login_fails_inactive_user(client, db_session):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Inactive User",
            "email": "inactive@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    user = db_session.query(User).filter(User.email == "inactive@example.com").first()
    user.is_active = False
    db_session.commit()

    resp = client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Inactive user account"


# 12. /api/auth/me succeeds with valid access token
def test_12_me_succeeds_with_valid_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Me User",
            "email": "me@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "me@example.com", "password": "Password123!"},
    ).json()["access_token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


# 13. /api/auth/me rejects missing token
def test_13_me_rejects_missing_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


# 14. /api/auth/me rejects malformed token
def test_14_me_rejects_malformed_token(client):
    resp = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer malformed.jwt.token"}
    )
    assert resp.status_code == 401


# 15. /api/auth/me rejects expired token
def test_15_me_rejects_expired_token(client, db_session):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Exp User",
            "email": "exp@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    user = db_session.query(User).filter(User.email == "exp@example.com").first()
    expired_token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        expires_delta=timedelta(seconds=-10),
    )
    resp = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


# 16. forgot-password returns generic response for an existing email
def test_16_forgot_password_generic_response_existing_email(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "FP User",
            "email": "fp_exist@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/forgot-password", json={"email": "fp_exist@example.com"}
    )
    assert resp.status_code == 200
    assert "password reset OTP has been generated" in resp.json()["message"]


# 17. forgot-password returns equivalent generic response for a nonexistent email
def test_17_forgot_password_generic_response_nonexistent_email(client):
    resp = client.post(
        "/api/auth/forgot-password", json={"email": "nonexistent@example.com"}
    )
    assert resp.status_code == 200
    assert "password reset OTP has been generated" in resp.json()["message"]


# 18. Existing-user forgot-password creates an OTP record
def test_18_existing_user_creates_otp_record(client, db_session):
    OTPService.clear_dev_otps()
    email = "otp_rec@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "OTP Rec User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    user = db_session.query(User).filter(User.email == email).first()
    client.post("/api/auth/forgot-password", json={"email": email})

    otp_record = (
        db_session.query(PasswordResetOTP)
        .filter(PasswordResetOTP.user_id == user.id)
        .order_by(PasswordResetOTP.id.desc())
        .first()
    )
    assert otp_record is not None
    assert otp_record.verified is False
    assert otp_record.used is False


# 19. Stored OTP value is hashed and is not equal to plaintext OTP
def test_19_stored_otp_is_hashed(client, db_session):
    OTPService.clear_dev_otps()
    email = "hashed_otp@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "Hashed OTP User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    user = db_session.query(User).filter(User.email == email).first()
    client.post("/api/auth/forgot-password", json={"email": email})

    plain_otp = OTPService.get_dev_otp(email)
    assert plain_otp is not None

    otp_record = (
        db_session.query(PasswordResetOTP)
        .filter(PasswordResetOTP.user_id == user.id)
        .order_by(PasswordResetOTP.id.desc())
        .first()
    )
    assert otp_record.otp != plain_otp
    assert len(otp_record.otp) == 64  # SHA-256 hex digest length


# 20. Correct OTP verification succeeds
def test_20_correct_otp_verification_succeeds(client):
    OTPService.clear_dev_otps()
    email = "correct_otp@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "Correct OTP User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})
    plain_otp = OTPService.get_dev_otp(email)

    resp = client.post("/api/auth/verify-otp", json={"email": email, "otp": plain_otp})
    assert resp.status_code == 200
    assert "reset_token" in resp.json()


# 21. Incorrect OTP verification fails
def test_21_incorrect_otp_verification_fails(client):
    OTPService.clear_dev_otps()
    email = "wrong_otp@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "Wrong OTP User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})

    resp = client.post("/api/auth/verify-otp", json={"email": email, "otp": "000000"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired OTP"


# 22. Expired OTP verification fails
def test_22_expired_otp_verification_fails(client, db_session):
    email = "expired_otp@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "Expired OTP User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    user = db_session.query(User).filter(User.email == email).first()

    expired_record = PasswordResetOTP(
        user_id=user.id,
        otp=hash_otp("888888"),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        verified=False,
        used=False,
    )
    db_session.add(expired_record)
    db_session.commit()

    resp = client.post("/api/auth/verify-otp", json={"email": email, "otp": "888888"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired OTP"


# 23. Successful OTP verification returns a password-reset token
def test_23_verify_otp_returns_reset_token(client):
    OTPService.clear_dev_otps()
    email = "ret_token@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "Ret Token User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})
    plain_otp = OTPService.get_dev_otp(email)

    resp = client.post("/api/auth/verify-otp", json={"email": email, "otp": plain_otp})
    assert resp.status_code == 200
    data = resp.json()
    assert "reset_token" in data
    assert data["token_type"] == "bearer"


# 24. Password-reset token has the correct token type/purpose
def test_24_reset_token_has_correct_type_claim(client):
    OTPService.clear_dev_otps()
    email = "type_claim@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "Type Claim User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})
    plain_otp = OTPService.get_dev_otp(email)

    reset_token = client.post(
        "/api/auth/verify-otp", json={"email": email, "otp": plain_otp}
    ).json()["reset_token"]

    from app.utils.security import decode_jwt_token

    decoded = decode_jwt_token(reset_token)
    assert decoded.get("type") == "password_reset"


# 25. Password-reset token cannot access /api/auth/me
def test_25_reset_token_cannot_access_me(client):
    OTPService.clear_dev_otps()
    email = "reset_no_me@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "No Me User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})
    plain_otp = OTPService.get_dev_otp(email)

    reset_token = client.post(
        "/api/auth/verify-otp", json={"email": email, "otp": plain_otp}
    ).json()["reset_token"]

    resp = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {reset_token}"}
    )
    assert resp.status_code == 401
    assert "Invalid token purpose" in resp.json()["detail"]


# 26. Normal access token cannot be used to reset a password
def test_26_access_token_cannot_reset_password(client):
    email = "access_no_reset@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "No Reset User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    access_token = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    ).json()["access_token"]

    resp = client.post(
        "/api/auth/reset-password",
        json={"reset_token": access_token, "new_password": "NewPassword123!"},
    )
    assert resp.status_code == 400
    assert "Invalid token purpose" in resp.json()["detail"]


# 27. Password reset succeeds using a valid reset token
def test_27_password_reset_succeeds(client):
    OTPService.clear_dev_otps()
    email = "reset_ok@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "Reset OK User",
            "email": email,
            "password": "OldPassword123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})
    plain_otp = OTPService.get_dev_otp(email)
    reset_token = client.post(
        "/api/auth/verify-otp", json={"email": email, "otp": plain_otp}
    ).json()["reset_token"]

    resp = client.post(
        "/api/auth/reset-password",
        json={"reset_token": reset_token, "new_password": "NewPassword123!"},
    )
    assert resp.status_code == 200
    assert "Password has been reset successfully" in resp.json()["message"]


# 28. Old password fails after reset
def test_28_old_password_fails_after_reset(client):
    OTPService.clear_dev_otps()
    email = "old_fail@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "Old Fail User",
            "email": email,
            "password": "OriginalPassword123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})
    plain_otp = OTPService.get_dev_otp(email)
    reset_token = client.post(
        "/api/auth/verify-otp", json={"email": email, "otp": plain_otp}
    ).json()["reset_token"]

    client.post(
        "/api/auth/reset-password",
        json={"reset_token": reset_token, "new_password": "BrandNewPassword123!"},
    )

    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": "OriginalPassword123!"},
    )
    assert resp.status_code == 401


# 29. New password succeeds after reset
def test_29_new_password_succeeds_after_reset(client):
    OTPService.clear_dev_otps()
    email = "new_succ@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "New Succ User",
            "email": email,
            "password": "OriginalPassword123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})
    plain_otp = OTPService.get_dev_otp(email)
    reset_token = client.post(
        "/api/auth/verify-otp", json={"email": email, "otp": plain_otp}
    ).json()["reset_token"]

    client.post(
        "/api/auth/reset-password",
        json={"reset_token": reset_token, "new_password": "BrandNewPassword123!"},
    )

    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": "BrandNewPassword123!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# 30. Same OTP/reset authorization cannot be reused after successful reset
def test_30_reset_authorization_cannot_be_reused(client):
    OTPService.clear_dev_otps()
    email = "no_reuse@example.com"
    client.post(
        "/api/auth/signup",
        json={
            "name": "No Reuse User",
            "email": email,
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    client.post("/api/auth/forgot-password", json={"email": email})
    plain_otp = OTPService.get_dev_otp(email)
    reset_token = client.post(
        "/api/auth/verify-otp", json={"email": email, "otp": plain_otp}
    ).json()["reset_token"]

    # First reset
    client.post(
        "/api/auth/reset-password",
        json={"reset_token": reset_token, "new_password": "FirstResetPass123!"},
    )

    # Second reset attempt with same reset token
    reuse_resp = client.post(
        "/api/auth/reset-password",
        json={"reset_token": reset_token, "new_password": "SecondResetPass123!"},
    )
    assert reuse_resp.status_code == 400
    assert "expired or already been used" in reuse_resp.json()["detail"].lower()


# 31. Logout without authentication fails
def test_31_logout_without_auth_fails(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401


# 32. Logout with valid authentication succeeds
def test_32_logout_with_auth_succeeds(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Logout User",
            "email": "logout@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "logout@example.com", "password": "Password123!"},
    ).json()["access_token"]

    resp = client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert "Logged out successfully" in resp.json()["message"]


# 33. Correct INVENTORY_MANAGER RBAC check succeeds
def test_33_rbac_inventory_manager_succeeds(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Mgr RBAC User",
            "email": "rbac_mgr@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "rbac_mgr@example.com", "password": "Password123!"},
    ).json()["access_token"]

    resp = client.get(
        "/test-rbac-manager-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Manager access granted"


# 34. Wrong role produces HTTP 403
def test_34_rbac_wrong_role_produces_403(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff RBAC User",
            "email": "rbac_staff@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "rbac_staff@example.com", "password": "Password123!"},
    ).json()["access_token"]

    resp = client.get(
        "/test-rbac-manager-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Insufficient privileges"


# 35. Unauthenticated RBAC access produces HTTP 401
def test_35_rbac_unauthenticated_produces_401(client):
    resp = client.get("/test-rbac-manager-only")
    assert resp.status_code == 401
