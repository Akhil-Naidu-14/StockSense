# StockSense API Documentation

## System Health

### Get Health Status

Checks the operational status of the StockSense API backend.

- **URL:** `/api/health`
- **Method:** `GET`
- **Authentication:** None
- **Response Headers:** `Content-Type: application/json`

#### Success Response (200 OK)

```json
{
  "status": "ok",
  "app_name": "StockSense API",
  "environment": "development"
}
```

---

## Authentication & Authorization (`/api/auth`)

### Bearer Authentication
Endpoints requiring authentication expect an HTTP `Authorization` header formatted as:
```text
Authorization: Bearer <access_token>
```

### Roles & RBAC
System operations are restricted based on user roles:
- `INVENTORY_MANAGER`: Complete administrative and managerial access across warehouses.
- `WAREHOUSE_STAFF`: Standard operational access for inventory recording and handling.

---

### 1. User Signup
Registers a new user account with a specified role.

- **URL:** `/api/auth/signup`
- **Method:** `POST`
- **Authentication:** None

#### Request Body
```json
{
  "name": "Akhil",
  "email": "user@example.com",
  "phone": "+1234567890",
  "password": "SecurePassword123!",
  "role": "INVENTORY_MANAGER"
}
```

#### Response (201 Created)
```json
{
  "id": 1,
  "name": "Akhil",
  "email": "user@example.com",
  "phone": "+1234567890",
  "role": "INVENTORY_MANAGER",
  "is_active": true,
  "created_at": "2026-09-26T10:00:00Z",
  "updated_at": "2026-09-26T10:00:00Z"
}
```

---

### 2. User Login
Authenticates user credentials and issues a JWT access token.

- **URL:** `/api/auth/login`
- **Method:** `POST`
- **Authentication:** None

#### Request Body
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

#### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "Akhil",
    "email": "user@example.com",
    "phone": "+1234567890",
    "role": "INVENTORY_MANAGER",
    "is_active": true,
    "created_at": "2026-09-26T10:00:00Z",
    "updated_at": "2026-09-26T10:00:00Z"
  }
}
```

---

### 3. Current User Profile
Retrieves the profile of the currently authenticated active user.

- **URL:** `/api/auth/me`
- **Method:** `GET`
- **Authentication:** Bearer Token required

#### Response (200 OK)
```json
{
  "id": 1,
  "name": "Akhil",
  "email": "user@example.com",
  "phone": "+1234567890",
  "role": "INVENTORY_MANAGER",
  "is_active": true,
  "created_at": "2026-09-26T10:00:00Z",
  "updated_at": "2026-09-26T10:00:00Z"
}
```

---

### 4. User Logout
Stateless logout notification endpoint.

- **URL:** `/api/auth/logout`
- **Method:** `POST`
- **Authentication:** Bearer Token required

#### Response (200 OK)
```json
{
  "message": "Logged out successfully. Please discard the access token on the client side."
}
```
*Note: Because JWT tokens are stateless, clients must discard the stored token from localStorage/sessionStorage upon calling logout.*

---

### 5. Forgot Password (OTP Generation)
Initiates the 6-digit numeric OTP password reset process.

- **URL:** `/api/auth/forgot-password`
- **Method:** `POST`
- **Authentication:** None

#### Request Body
```json
{
  "email": "user@example.com"
}
```

#### Response (200 OK)
```json
{
  "message": "If the email is registered, a password reset OTP has been generated."
}
```
*Note: To prevent account enumeration attacks, a uniform response is returned regardless of whether the email exists in the database.*

#### Development/Test OTP Behavior
In `development` / `test` environments (`APP_ENV != "production"`), the generated OTP is logged to backend console and stored in `OTPService._dev_otp_store`. Production API responses never leak OTP codes.

---

### 6. Verify OTP
Verifies the 6-digit OTP code and returns a short-lived, single-purpose password reset token.

- **URL:** `/api/auth/verify-otp`
- **Method:** `POST`
- **Authentication:** None

#### Request Body
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

#### Response (200 OK)
```json
{
  "reset_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "message": "OTP verified successfully."
}
```
*Note: The returned `reset_token` has claim `"type": "password_reset"` and cannot be used as an access token for general API routes.*

---

### 7. Reset Password
Resets user password using the short-lived password reset token.

- **URL:** `/api/auth/reset-password`
- **Method:** `POST`
- **Authentication:** None

#### Request Body
```json
{
  "reset_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "NewSecurePassword123!"
}
```

#### Response (200 OK)
```json
{
  "message": "Password has been reset successfully."
}
```
*Note: Once reset completes, the OTP record is marked as `used=True`, rendering the reset token and OTP single-use.*
